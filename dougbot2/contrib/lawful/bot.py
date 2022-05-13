# bot.py
# Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import io
import re
from collections import defaultdict, deque
from contextlib import contextmanager, suppress
from datetime import datetime
from typing import Literal, Optional, Union
from urllib.parse import urlsplit

import attr
import pandas as pd
import pytz
import simplejson as json
from bs4 import BeautifulSoup
from discord import (
    AllowedMentions,
    CategoryChannel,
    File,
    Forbidden,
    Guild,
    Member,
    Message,
    Object,
    PartialMessage,
    PermissionOverwrite,
    Role,
    StageChannel,
    TextChannel,
    VoiceChannel,
)
from discord.ext.commands import Greedy, command, is_owner
from discord.utils import snowflake_time
from django.utils.timezone import get_current_timezone
from more_itertools import first

from dougbot2.discord.cog import Gear
from dougbot2.discord.context import Circumstances
from dougbot2.exts import autodoc as doc
from dougbot2.utils.common import (
    Embed2,
    PermissionOverride,
    Permissions2,
    assumed_utc,
    can_embed,
    chapterize_items,
    code,
    iter_urls,
    strong,
    tag,
    timestamp,
    traffic_light,
    trunc_for_field,
    utcnow,
)
from dougbot2.utils.converters import Choice, Datetime
from dougbot2.utils.markdown import TIMESTAMP_PROCESSOR

from .. import facts

AnyChannel = Union[TextChannel, VoiceChannel, StageChannel, CategoryChannel]


def shorten_list(items: list[str], size: int) -> list[str]:
    if len(items) <= size:
        return items
    return [*items[:size], f"({len(items) - size} more)"]


def subchannels(*channels: AnyChannel):
    for c in channels:
        if isinstance(c, CategoryChannel):
            yield from c.channels
        yield c


class StreamClock:
    def __init__(self, date: Optional[datetime] = None):
        now = (date or utcnow()).astimezone(pytz.timezone(facts.TIMEZONE))
        self.stream = now.replace(hour=12, minute=0, second=0, microsecond=0)
        self.notify = now.replace(hour=9, minute=0, second=0, microsecond=0)

    @property
    def is_dst(self):
        return self.stream.dst()


def domain_under(d: str, matches: list[str]) -> bool:
    return any(d == dx or d.endswith(f".{dx}") for dx in matches)


@attr.s(auto_attribs=True)
class _Channel:
    id: int
    kind: str
    name: str
    desc: Optional[str]
    cat: Optional[int]
    perms: dict[int, tuple[int, int]]
    order: int


@attr.s(auto_attribs=True)
class _Role:
    id: int
    name: int
    color: int
    perms: int
    order: int
    hoisted: bool
    pingable: bool


@contextmanager
def open_file(data: bytes, filename: str):
    try:
        with io.BytesIO(data) as blob:
            blob.seek(0)
            yield File(blob, filename)
    finally:
        pass


class Lawful(
    Gear,
    name="District: Lawful",
    order=4,
    description="Exclusive to the Doug District.",
):
    RE_EVERYONE = re.compile(r"@everyone|@here")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.flood_buckets: defaultdict[int, deque[tuple[int, int]]] = defaultdict(
            lambda: deque(maxlen=3)
        )

    @command("ontime", aliases=("whenstream",))
    @doc.description("Show when Doug usually streams in your local time.")
    @can_embed
    async def ontime(self, ctx: Circumstances):
        clock = StreamClock()
        if clock.is_dst:
            dst = "in effect"
        else:
            dst = "not in effect"
        res: list[str] = [
            f'Doug usually {strong("starts streaming")} at around {timestamp(clock.stream, "hh:mm")}',
            f'We will {strong("notify you in advance")} at around {timestamp(clock.notify, "hh:mm")} (+/- 1 hour)',
            f"Daylight savings time is currently {strong(dst)} where Doug lives.",
        ]
        embed = Embed2(description="\n".join(res)).decorated(ctx.guild)
        await ctx.response(ctx, embed=embed).reply().run()

    @Gear.listener("on_message")
    async def message_dispatch(self, msg: Message):
        if msg.author.bot:
            return
        await self.broadcast(msg)
        with suppress(StopIteration):
            await self.discord_domain_security(msg)
            await self.everyone_ping_spam(msg)

    @Gear.listener("on_message_edit")
    async def message_edit_dispatch(self, before: Message, after: Message):
        if after.author.bot:
            return
        if before.content == after.content:
            return
        with suppress(StopIteration):
            await self.discord_domain_security(after)
            await self.everyone_ping_spam(after)

    WHITELISTED_DOMAINS = (
        "discord.com",
        "discordapp.com",
        "discord.gg",
        "discord.gift",
        "discord.gifts",
        "dis.gd",
        "discordstatus.com",
        "discord.media",
        "discordpy.readthedocs.io",
        "discord.new",
        "discordmerch.com",
    )
    RE_SUSPICIOUS_DOMAIN = re.compile(
        r"d.?[i1l].?s+.?[ck].?[o0].?r.?(?:d|cl)", re.IGNORECASE
    )

    def _test_discord_url(self, text: str) -> Optional[str]:
        suspicious = None
        for u in iter_urls(text):
            url = urlsplit(u)
            domain = url.netloc
            if bool(self.RE_SUSPICIOUS_DOMAIN.match(domain)) and not domain_under(
                domain, self.WHITELISTED_DOMAINS
            ):
                suspicious = url.geturl()
                break
        return suspicious

    async def discord_domain_security(self, msg: Message):
        author: Member = msg.author
        guild: Guild = msg.guild
        if guild.id != facts.GUILD_ID:
            return

        if not (suspicious := self._test_discord_url(msg.content)):
            return

        REASON = (
            f'{strong("Doug District: Heightened Security")}'
            "\n\nWe are currently preventing anyone from sending messages"
            " containing suspicious URLs that resemble official Discord sites."
            "\n\nThe following URL is matched from your message:"
            f" {code(suspicious)}"
            "\n\nYou have been banned. Moderators will review your message"
            " and determine further actions. If you have been wrongly flagged,"
            " you may expect to be unbanned at a reasonable time"
            " (usually within 48 hours)."
        )

        try:
            await msg.delete()
        except Exception as e:
            self.log.warning(e, exc_info=e)
            did_delete = False
        else:
            did_delete = True

        try:
            await author.send(REASON)
        except Exception as e:
            self.log.warning(e, exc_info=e)
            did_warn = False
        else:
            did_warn = True

        try:
            await author.ban(
                reason="Scam/phishing: compromised account", delete_message_days=0
            )
        except Exception as e:
            self.log.warning(e, exc_info=e)
            did_ban = False
        else:
            did_ban = True

        what = (
            strong(
                f"Message contains URL {code(suspicious)}, whose domain is not whitelisted."
            )
            + f'\nWhitelisted domains are: {", ".join(self.WHITELISTED_DOMAINS)}'
        )

        report = (
            Embed2(title="Security: Suspicious URL: Scam/phishing")
            .add_field(name="Who", value=tag(author), inline=False)
            .add_field(name="Where", value=tag(msg.channel), inline=True)
            .add_field(
                name="When",
                value=timestamp(assumed_utc(msg.created_at), "relative"),
                inline=True,
            )
            .add_field(name="What", value=what, inline=False)
            .add_field(name="Deleted", value=traffic_light(did_delete))
            .add_field(name="Notified", value=traffic_light(did_warn))
            .add_field(name="Banned", value=traffic_light(did_ban))
            .add_field(
                name="Original message",
                value=trunc_for_field(msg.content),
                inline=False,
            )
            .set_timestamp()
            .decorated(guild)
        )

        notif_channel: TextChannel = guild.get_channel(facts.CHANNEL_BOT_STUFF)
        notif_target: Role = guild.get_role(facts.ROLE_EMERGENCY)

        await notif_channel.send(
            content=tag(notif_target),
            embed=report,
            allowed_mentions=AllowedMentions(roles=[notif_target]),
        )
        raise StopIteration

    async def everyone_ping_spam(self, msg: Message):
        if msg.guild.id != facts.GUILD_ID:
            return
        if not self.RE_EVERYONE.search(msg.content):
            return
        bucket = self.flood_buckets[msg.author.id]
        bucket.append((msg.channel.id, msg.id))
        if len(bucket) < 3:
            return
        previous_timestamps = [snowflake_time(id_).timestamp() for _, id_ in bucket]
        if datetime.now().timestamp() - min(previous_timestamps) > 180:
            return

        guild: Guild = msg.guild
        mute: Role = guild.get_role(facts.ROLE_MUTED)
        msgs = [
            PartialMessage(channel=guild.get_channel(channel_id), id=id_)
            for channel_id, id_ in bucket
        ]

        REASON = (
            f'{strong("Doug District: Security")}'
            "\n\nYou have been muted for spamming @everyone. The last message was:"
            f"\n{code(msg.content)}"
            f"\n\nMods will review the messages and see if you should be unmuted."
        )

        for m in msgs:
            try:
                await m.delete()
            except Exception:
                did_delete = False
            else:
                did_delete = True

        try:
            await msg.author.add_roles(mute, reason="Spamming @everyone")
            await msg.author.send(REASON)
        except Exception:
            did_mute = False
        else:
            did_mute = True

        what = strong(
            "Sending 3 or more messages containing @everyone within 3 minutes"
        )

        report = (
            Embed2(title="Security: @everyone spam")
            .add_field(name="Who", value=tag(msg.author), inline=False)
            .add_field(name="Where", value=tag(msg.channel), inline=True)
            .add_field(
                name="When",
                value=timestamp(assumed_utc(msg.created_at), "relative"),
                inline=True,
            )
            .add_field(name="What", value=what, inline=False)
            .add_field(name="Deleted", value=traffic_light(did_delete))
            .add_field(name="Muted", value=traffic_light(did_mute))
            .add_field(
                name="Original message",
                value=trunc_for_field(msg.content),
                inline=False,
            )
            .set_timestamp()
            .decorated(guild)
        )

        notif_channel: TextChannel = guild.get_channel(facts.CHANNEL_BOT_STUFF)
        notif_target: Role = guild.get_role(facts.ROLE_EMERGENCY)

        await notif_channel.send(
            content=tag(notif_target),
            embed=report,
            allowed_mentions=AllowedMentions(roles=[notif_target]),
        )
        raise StopIteration

    async def broadcast(self, msg: Message):
        if msg.channel.id != facts.CHANNEL_ANNOUNCEMENTS:
            return
        guild: Guild = msg.guild
        if msg.author == guild.owner:
            await msg.publish()

    @command("slice")
    @doc.description("Export a slice of channel messages as an HTML file")
    @doc.argument("start", "The beginning message (included).")
    @doc.argument("end", "The ending message (included).")
    @doc.hidden
    @doc.restriction(is_owner)
    async def timeline_slice(
        self,
        ctx: Circumstances,
        start: Message,
        end: Message,
    ):
        if start.channel != end.channel:
            raise doc.NotAcceptable("Messages are in different channels.")
        STYLESHEET = """
        html {
            color: #d3d3d3;
            background-color: #37393e;
            font-family: 'Whitney', 'Lato', 'Helvetica Neue', 'Helvetica', -apple-system,
            BlinkMacSystemFont, 'Noto Sans', 'Ubuntu', 'Open Sans', sans-serif;
        }

        body {
            box-sizing: border-box;
        }

        article {
            margin: 2rem 3vw 2rem;
        }

        .message {
            display: flex;
            flex-flow: row nowrap;
            justify-content: flex-start;
            align-items: baseline;
            gap: 0.3rem;
            margin: 0.5rem 0;
        }

        .message-time {
            font-size: 0.8rem;
            letter-spacing: -0.1px;
            flex: 0 0 9rem;
            text-align: end;
        }

        .message-main {
            display: flex;
            flex-flow: row nowrap;
            justify-content: flex-start;
            align-items: baseline;
            gap: 0.6rem;
        }

        .message-author {
            flex: 0 0 auto;
        }

        .message-content {
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .time-range {
            color: #11c9ee;
        }
        """
        tz = get_current_timezone()
        channel: TextChannel = start.channel
        start_time = assumed_utc(start.created_at).astimezone(tz)
        end_time = assumed_utc(end.created_at).astimezone(tz)
        title = (
            f"{ctx.guild.name} #{channel.name}"
            f' {start_time.strftime("%c")}'
            f' to {end_time.strftime("%c")}'
        )
        soup = BeautifulSoup(
            f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{title}</title>
                <style>{STYLESHEET}</style>
            </head>
            <body>
                <article>
                    <header>
                        <h2 class="channel-name">#general</h2>
                        <p>
                            From: <em class="time-range">{start_time.strftime("%c")}</em>
                            <br>
                            To: <em class="time-range">{end_time.strftime("%c")}</em>
                            <br>
                            Timezone: <em class="time-range">Pacific</em>
                        </p>
                        <p>
                            Content descriptors: <strong>__</strong>
                        </p>
                    </header>
                </article>
            </body>
            </html>
        """,
            features="lxml",
        )
        body = soup.html.body.article
        async with ctx.typing():
            async for msg in channel.history(
                limit=None, after=Object(start.id - 1), before=end, oldest_first=True
            ):
                msg: Message
                ctime = assumed_utc(msg.created_at).astimezone(tz)
                timestamp = soup.new_tag(
                    "time", attrs={"class": "message-time"}, datetime=ctime.isoformat()
                )
                timestamp.append(ctime.strftime("%y/%m/%d %H:%M:%S %Z"))
                author = soup.new_tag(
                    "span",
                    attrs={
                        "class": "message-author",
                        "data-user-id": str(msg.author.id),
                    },
                    title=msg.author.display_name,
                    style=f"color: #{msg.author.color.value:06x};",
                )
                author_name = soup.new_tag("strong")
                author_name.append(str(msg.author))
                author.append(author_name)
                content = soup.new_tag(
                    "code",
                    attrs={"class": "message-content", "data-msg-id": str(msg.id)},
                )
                content.append(msg.content)
                main = soup.new_tag("span", attrs={"class": "message-main"})
                main.extend([author, content])
                container = soup.new_tag("p", attrs={"class": "message"})
                container.extend([timestamp, main])
                body.append(container)
        with io.StringIO(str(soup)) as stream:
            stream.seek(0)
            filename = f"{title}.html"
            file = File(stream, filename=filename)
            await ctx.send(file=file)

    @command("stats")
    @doc.hidden
    @doc.restriction(is_owner)
    async def stats(
        self, ctx: Circumstances, channel_id: int, start: int, end: Optional[int]
    ):
        guild: Guild = ctx.bot.get_guild(facts.GUILD_ID)
        channel: TextChannel = guild.get_channel(channel_id)
        start_date = datetime.fromtimestamp(start)
        end_date = datetime.fromtimestamp(end) if end else datetime.now()
        data: list[tuple[int, str, datetime, int, bool, str, bool, bool]] = []

        def is_subscriber(author: Member):
            if not hasattr(author, "roles"):
                return False
            return facts.ROLE_SUBSCRIBER in (r.id for r in author.roles)

        def is_booster(author: Member):
            if not hasattr(author, "roles"):
                return False
            return facts.ROLE_BOOSTER in (r.id for r in author.roles)

        async with ctx.typing():
            async for msg in channel.history(
                limit=None, after=start_date, before=end_date
            ):
                msg: Message
                author_id = msg.author.id
                author = str(msg.author)
                timestamp = assumed_utc(msg.created_at)
                length = len(msg.content)
                has_uploads = bool(msg.attachments)
                link = msg.jump_url
                sub = is_subscriber(msg.author)
                boost = is_booster(msg.author)
                data.append(
                    (
                        author_id,
                        author,
                        timestamp,
                        length,
                        has_uploads,
                        link,
                        sub,
                        boost,
                    )
                )

        df = pd.DataFrame(
            data,
            columns=[
                "author_id",
                "author",
                "timestamp",
                "length",
                "has_uploads",
                "link",
                "subscriber",
                "booster",
            ],
        )
        num_messages = df.loc[:, "author"].value_counts().rename("num_messages")
        num_chars = df.groupby(["author"]).sum().loc[:, "length"].rename("num_chars")
        by_hour = (
            df.set_index("timestamp")
            .groupby([pd.Grouper(freq="1H"), "author"])["author_id"]
            .agg(lambda c: 1)
            .unstack()
            .fillna(0)
            .sum()
            .rename("active_hours")
            .astype(int)
        )
        by_day = (
            df.set_index("timestamp")
            .groupby([pd.Grouper(freq="1D"), "author"])["author_id"]
            .agg(lambda c: 1)
            .unstack()
            .fillna(0)
            .sum()
            .rename("active_days")
            .astype(int)
        )
        subscribers = (
            df.groupby("author")
            .first()
            .loc[:, "subscriber"]
            .map({True: "yes", False: "no"})
        )
        boosters = (
            df.groupby("author")
            .first()
            .loc[:, "booster"]
            .map({True: "yes", False: "no"})
        )
        summaries = pd.concat(
            [num_messages, num_chars, by_hour, by_day, subscribers, boosters],
            axis="columns",
        )
        file1 = (
            f"counts.{channel.name}.{start_date.isoformat()}.{end_date.isoformat()}.csv"
        )
        file2 = (
            f"stats.{channel.name}.{start_date.isoformat()}.{end_date.isoformat()}.csv"
        )
        with open_file(df.to_csv().encode(), file1) as f1, open_file(
            summaries.to_csv().encode(), file2
        ) as f2:
            return await ctx.send(files=[f1, f2])

    @command("roster")
    @doc.description("List all members of a role.")
    @doc.hidden
    @doc.restriction(is_owner)
    async def roster(self, ctx: Circumstances, role: Role, limit: int = 0):
        tags: list[str] = [m.mention for m in role.members]
        if limit:
            tags = tags[:limit]
        pages = chapterize_items(tags, 720)
        for p in pages:
            res = " ".join(p)
            await ctx.send(res, allowed_mentions=AllowedMentions.none())

    @command("incognito")
    @doc.description("Hide a member from server channels.")
    @doc.argument("member", "The member to hide.")
    @doc.argument(
        "scope",
        (
            "The scope of the channels to apply this command: "
            '"everywhere" to hide the member from all channels, '
            '"nowhere" to reveal the member in all channels (disabling Incognito), '
            '"in" to hide the member from the channel listed after this argument, '
            '"except" to hide the member from all channels except the ones listed after '
            "this argument."
        ),
    )
    @doc.hidden
    @doc.restriction(is_owner)
    async def incognito(
        self,
        ctx: Circumstances,
        member: Member,
        scope: Choice[Literal["everywhere", "nowhere", "in", "except"]],
        channels: Greedy[AnyChannel],
    ):
        targets: set[AnyChannel] = set()
        if scope == "everywhere":
            targets.update(ctx.guild.channels)
        elif scope == "in":
            targets.update(subchannels(*channels))
        elif scope == "except":
            targets.update(ctx.guild.channels)
            targets.difference_update(subchannels(*channels))
        failed: list[AnyChannel] = []
        async with ctx.typing():
            for c in ctx.guild.channels:
                c: AnyChannel
                if not c.permissions_for(ctx.me).manage_roles:
                    failed.append(c)
                    continue
                perms = PermissionOverride.upgrade(c.overwrites_for(member))
                updated = perms.evolve(view_channel=c not in targets and None)
                if not (perms.denied.view_channel ^ updated.denied.view_channel):
                    continue
                try:
                    await c.set_permissions(
                        member, reason="Incognito", overwrite=updated or None
                    )
                except Forbidden:
                    failed.append(c)
        if not failed:
            return await ctx.response(ctx).success().run()
        else:
            res = (
                "The following channels are not updated because "
                "the bot has insufficient permissions:\n"
                f'{" ".join(shorten_list([c.mention for c in failed], 15))}'
            )
            return await ctx.response(ctx, content=res).run()

    @command("timestamp")
    @doc.description(
        "Convert a date expressed in English to Discord timestamp markups."
    )
    @doc.argument("date_time", "Text indicating a date and/or time.")
    @doc.invocation(("date_time",), None)
    async def timestamp(self, ctx: Circumstances, *, date_time: Datetime):
        dt = date_time.value
        if not (tzname := dt.tzname()):
            tzinfo = (
                f'{strong("No timezone provided")}\nTime will be in server'
                f" timezone {strong(get_current_timezone().tzname(dt))}"
            )
        else:
            tzinfo = f"Timezone: {strong(tzname)}"
        formats: list[str] = [tzinfo]
        for k in TIMESTAMP_PROCESSOR:
            formatted = timestamp(dt, k)
            formats.append(f"{code(formatted)} {formatted}")
        res = Embed2(description="\n".join(formats))
        return await ctx.response(ctx, embed=res).reply().run()

    @command("pickle")
    @doc.restriction(is_owner)
    @doc.hidden
    async def pickle(self, ctx: Circumstances):
        guild: Guild = ctx.guild

        channels = []
        for c in guild.channels:
            c: AnyChannel
            perms = {}
            for r, p in c.overwrites.items():
                if not isinstance(r, Role):
                    continue
                allowed, denied = PermissionOverride.upgrade(p).pair()
                perms[r.id] = (allowed.value, denied.value)
            channel = _Channel(
                c.id,
                type(c).__name__,
                c.name,
                getattr(c, "topic", None),
                c.category_id,
                perms,
                c.position,
            )
            channels.append(attr.asdict(channel))

        roles = []
        for r in guild.roles:
            r: Role
            role = _Role(
                r.id,
                r.name,
                r.color.value,
                r.permissions.value,
                r.position,
                r.hoist,
                r.mentionable,
            )
            roles.append(attr.asdict(role))

        info = {"channels": channels, "roles": roles}
        with open_file(
            json.dumps(info).encode(), f"export.{utcnow().isoformat()}.json"
        ) as f:
            return await ctx.send(file=f)

    @command("unpickle")
    @doc.restriction(is_owner)
    @doc.hidden
    async def unpickle(self, ctx: Circumstances):
        msg = ctx.message
        guild: Guild = ctx.guild
        if not (upload := first(msg.attachments)):
            return
        info = json.loads((await upload.read()).decode("utf8"))

        mapped: dict[int, Union[AnyChannel, Role]] = {}

        await ctx.send("Creating roles")
        roles = [_Role(**r) for r in info["roles"]]
        for r in sorted(roles, key=lambda r: r.order, reverse=True):
            try:
                created = await guild.create_role(
                    name=r.name,
                    permissions=Permissions2(r.perms),
                    colour=r.color,
                    hoist=r.hoisted,
                    mentionable=r.pingable,
                )
            except Exception as e:
                await ctx.send(f":warning: Error creating role {r.name}: {e}")
                continue
            mapped[r.id] = created

        async def get_override(perms: dict[str, tuple[int, int]]):
            overrides = {}
            for target_id, (allowed, denied) in perms.items():
                role: Role = mapped.get(int(target_id))
                if not role:
                    continue
                override = PermissionOverride.from_pair(
                    Permissions2(allowed), Permissions2(denied)
                )
                overrides[role] = override
            return overrides

        await ctx.send("Creating channels")
        channels = [_Channel(**c) for c in info["channels"]]
        for c in channels:
            func = {
                "CategoryChannel": Guild.create_category,
                "TextChannel": Guild.create_text_channel,
                "VoiceChannel": Guild.create_voice_channel,
                "StageChannel": Guild.create_stage_channel,
            }[c.kind]
            kwargs = {"name": c.name, "overwrites": await get_override(c.perms)}
            if c.kind == "TextChannel":
                kwargs["topic"] = c.desc
            try:
                created = await func(guild, **kwargs)
            except Exception as e:
                await ctx.send(f":warning: Error creating channel {c.name}: {e}")
                continue
            mapped[c.id] = created

        await ctx.send("Assigning categories")
        for c in filter(lambda c: c.kind != "CategoryChannel", channels):
            if not c.cat:
                continue
            if not (category := mapped.get(c.cat)):
                await ctx.send(
                    f":warning: Skipping category {c.cat} as it was not created"
                )
                continue
            if not (channel := mapped.get(c.id)):
                await ctx.send(
                    f":warning: Skipping channel {c.name} as it was not created"
                )
                continue
            try:
                await channel.edit(category=category)
            except Exception as e:
                await ctx.send(
                    f":warning: Error assigning category {c.cat} - {c.name}: {e}"
                )

        await ctx.send("Assigning positions")
        for c in sorted(
            filter(lambda c: c.kind == "CategoryChannel", channels),
            key=lambda c: c.order,
        ):
            if not (channel := mapped.get(c.id)):
                await ctx.send(
                    f":warning: Skipping channel {c.name} as it was not created"
                )
                continue
            try:
                await channel.edit(position=c.order)
            except Exception as e:
                await ctx.send(f":warning: Error assigning position for {c.name}: {e}")
        for c in sorted(
            filter(lambda c: c.kind != "CategoryChannel", channels),
            key=lambda c: c.order,
        ):
            if not (channel := mapped.get(c.id)):
                await ctx.send(
                    f":warning: Skipping channel {c.name} as it was not created"
                )
                continue
            try:
                await channel.edit(position=c.order)
            except Exception as e:
                await ctx.send(f":warning: Error assigning position for {c.name}: {e}")

    @command("blackout")
    @doc.restriction(is_owner)
    @doc.hidden
    async def blackout(
        self, ctx: Circumstances, targets: Greedy[Role], exemptions: Greedy[AnyChannel]
    ):
        overrides = {r: PermissionOverwrite(read_messages=False) for r in targets}
        exemptions = {c.id for c in exemptions}
        for c in ctx.guild.channels:
            if c.id in exemptions:
                continue
            await c.edit(overwrites={**c.overwrites, **overrides})

    @command("restore")
    @doc.restriction(is_owner)
    @doc.hidden
    async def restore(
        self, ctx: Circumstances, targets: Greedy[Role], exemptions: Greedy[AnyChannel]
    ):
        overrides = {r: PermissionOverwrite(read_messages=None) for r in targets}
        exemptions = {c.id for c in exemptions}
        for c in ctx.guild.channels:
            if c.id in exemptions:
                continue
            await c.edit(overwrites={**c.overwrites, **overrides})

    @command("rollback")
    @doc.restriction(is_owner)
    @doc.hidden
    async def rollback(self, ctx: Circumstances):
        guild: Guild = ctx.guild
        DANNYLING: Role = guild.get_role(720807137319583804)
        SPOONIE: Role = guild.get_role(896787752929079296)
        PEPTO: Role = guild.get_role(591476142762885121)
        TWITCH_VIP: Role = guild.get_role(776937844219314217)
        GAMING_GOD: Role = guild.get_role(571872801741471744)
        FOUNDER: Role = guild.get_role(571242658094120960)
        MINECRAFT: Role = guild.get_role(698681714616303646)
        MC_MOD: Role = guild.get_role(718294100058570824)
        MC_DEV: Role = guild.get_role(678734357950627890)
        MC_BUILDER: Role = guild.get_role(717504053906767952)
        MC_CODER: Role = guild.get_role(717504150421635102)
        GAME_EVENT_ORG: Role = guild.get_role(777205626454933524)
        GAME_EVENT: Role = guild.get_role(755419145218293820)
        MOD: Role = guild.get_role(718291172124131408)
        POWER_BOT: Role = guild.get_role(872514540410134573)
        MUSIC_BOT: Role = guild.get_role(846485019093368874)
        VERIFICATION: Role = guild.get_role(723656315301265500)

        announcement: TextChannel = guild.get_channel(731407385624838197)
        content: TextChannel = guild.get_channel(567144073857859609)
        tweets: TextChannel = guild.get_channel(760774337627422731)
        server_news: TextChannel = guild.get_channel(880127379119415306)
        welcome: TextChannel = guild.get_channel(567141138021089310)
        role_assignment: TextChannel = guild.get_channel(675853120907116545)
        verification: TextChannel = guild.get_channel(721485737907978342)

        hangouts: CategoryChannel = guild.get_channel(567141138021089309)
        elites_club: TextChannel = guild.get_channel(755153467420573716)

        seasonal: CategoryChannel = guild.get_channel(755189447297073223)
        game_event_info: TextChannel = guild.get_channel(755419014200819732)
        game_event_org: TextChannel = guild.get_channel(813798988720898078)

        serious: CategoryChannel = guild.get_channel(750191779848126498)

        suggestions: CategoryChannel = guild.get_channel(571869415650361354)
        submit_and_discuss: TextChannel = guild.get_channel(833152757648326656)

        minecraft: CategoryChannel = guild.get_channel(743938486888824923)
        mc_info: TextChannel = guild.get_channel(743938486888824923)
        mc_suggest: TextChannel = guild.get_channel(743972630687907890)
        mc_coder: TextChannel = guild.get_channel(778362788317495296)
        mc_builder: TextChannel = guild.get_channel(729425259496865842)
        mc_devs: TextChannel = guild.get_channel(717503677199417445)
        mc_mods: TextChannel = guild.get_channel(717525537618395177)
        mc_dev_room: VoiceChannel = guild.get_channel(693945461043757066)

        nightbot: TextChannel = guild.get_channel(838102476640878623)
        voice_channels: CategoryChannel = guild.get_channel(750181268679032844)
        tahiti_text: TextChannel = guild.get_channel(829702176858308648)
        tahiti: VoiceChannel = guild.get_channel(567144551110934538)

        everyone = guild.default_role

        broadcasting_perms = {
            everyone: PermissionOverwrite(
                read_messages=True,
                read_message_history=True,
            ),
            DANNYLING: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                external_emojis=False,
                read_message_history=True,
            ),
            MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
            POWER_BOT: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
        }

        welcome_perms = {
            **broadcasting_perms,
            MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
            ),
        }

        verification_perms = {
            everyone: PermissionOverwrite(read_messages=False),
            VERIFICATION: PermissionOverwrite(read_messages=True),
        }

        role_assignment_perms = {
            **broadcasting_perms,
            DANNYLING: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                add_reactions=False,
                read_message_history=True,
            ),
        }

        suggestion_perms = {
            everyone: PermissionOverwrite(
                read_messages=False,
            ),
            DANNYLING: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                add_reactions=False,
            ),
            MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
            POWER_BOT: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
        }

        regular_perms = {
            everyone: PermissionOverwrite(
                read_messages=False,
            ),
            DANNYLING: PermissionOverwrite(
                read_messages=True,
            ),
            MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
                connect=True,
                speak=True,
                stream=True,
                priority_speaker=True,
            ),
            POWER_BOT: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
                connect=True,
                speak=True,
                stream=True,
                priority_speaker=True,
            ),
        }

        elevated_perms = {
            everyone: PermissionOverwrite(
                read_messages=False,
            ),
            DANNYLING: PermissionOverwrite(
                read_messages=False,
            ),
            SPOONIE: PermissionOverwrite(
                read_messages=True,
            ),
            PEPTO: PermissionOverwrite(
                read_messages=True,
            ),
            TWITCH_VIP: PermissionOverwrite(
                read_messages=True,
            ),
            GAMING_GOD: PermissionOverwrite(
                read_messages=True,
            ),
            FOUNDER: PermissionOverwrite(
                read_messages=True,
            ),
            MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
            POWER_BOT: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
        }

        game_event_perms = {
            everyone: PermissionOverwrite(
                read_messages=False,
            ),
            GAME_EVENT: PermissionOverwrite(
                read_messages=True,
                connect=True,
                speak=True,
                stream=True,
            ),
            GAME_EVENT_ORG: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                external_emojis=True,
                manage_messages=True,
                manage_roles=True,
                priority_speaker=True,
                mute_members=True,
                move_members=True,
                deafen_members=True,
            ),
            MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
                priority_speaker=True,
                mute_members=True,
                move_members=True,
                deafen_members=True,
            ),
            MUSIC_BOT: PermissionOverwrite(
                read_messages=True,
            ),
            POWER_BOT: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
        }

        game_event_info_perms = {
            **broadcasting_perms,
            GAME_EVENT_ORG: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                external_emojis=True,
                manage_messages=True,
                manage_roles=True,
            ),
        }

        game_event_org_perms = {
            everyone: PermissionOverwrite(
                read_messages=False,
            ),
            GAME_EVENT_ORG: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                external_emojis=True,
                manage_messages=True,
                manage_roles=True,
            ),
            MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
            MUSIC_BOT: PermissionOverwrite(
                read_messages=True,
            ),
            POWER_BOT: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                add_reactions=True,
                external_emojis=True,
                read_message_history=True,
            ),
        }

        minecraft_perms = {
            everyone: PermissionOverwrite(
                read_messages=False,
            ),
            MINECRAFT: PermissionOverwrite(
                read_messages=True,
                connect=True,
                speak=True,
                stream=True,
            ),
            MC_MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=True,
                manage_messages=True,
                priority_speaker=True,
                mute_members=True,
                move_members=True,
                deafen_members=True,
            ),
        }

        mc_info_perms = {
            **minecraft_perms,
            DANNYLING: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                add_reactions=False,
            ),
        }

        mc_suggest_perms = {
            everyone: PermissionOverwrite(
                read_messages=False,
            ),
            MINECRAFT: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
            ),
            MC_MOD: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
            ),
        }

        mc_coder_perms = {
            **minecraft_perms,
            MINECRAFT: PermissionOverwrite(read_messages=False),
            MC_CODER: PermissionOverwrite(read_messages=True),
        }
        mc_builder_perms = {
            **minecraft_perms,
            MINECRAFT: PermissionOverwrite(read_messages=False),
            MC_BUILDER: PermissionOverwrite(read_messages=True),
        }
        mc_devs_perms = {
            **minecraft_perms,
            MINECRAFT: PermissionOverwrite(read_messages=False),
            MC_DEV: PermissionOverwrite(read_messages=True),
        }
        mc_mods_perms = {
            **minecraft_perms,
            MINECRAFT: PermissionOverwrite(read_messages=False),
            MC_MOD: PermissionOverwrite(read_messages=True),
        }

        tahiti_perms = {
            everyone: PermissionOverwrite(read_messages=False),
            DANNYLING: PermissionOverwrite(
                read_messages=True,
                send_messages=False,
                add_reactions=False,
                connect=True,
                speak=False,
                stream=False,
            ),
        }

        await announcement.edit(overwrites=broadcasting_perms)
        await content.edit(overwrites=broadcasting_perms)
        await tweets.edit(overwrites=broadcasting_perms)
        await server_news.edit(overwrites=broadcasting_perms)
        await welcome.edit(overwrites=welcome_perms)
        await role_assignment.edit(overwrites=role_assignment_perms)
        await verification.edit(overwrites=verification_perms)

        await hangouts.edit(overwrites=regular_perms)
        for c in hangouts.channels:
            await c.edit(sync_permissions=True)
        await elites_club.edit(overwrites=elevated_perms)

        await seasonal.edit(overwrites=game_event_perms)
        for c in seasonal.channels:
            await c.edit(sync_permissions=True)
        await game_event_info.edit(overwrites=game_event_info_perms)
        await game_event_org.edit(overwrites=game_event_org_perms)

        await serious.edit(overwrites=regular_perms)
        for c in serious.channels:
            await c.edit(sync_permissions=True)

        await suggestions.edit(overwrites=suggestion_perms)
        for c in suggestions.channels:
            await c.edit(sync_permissions=True)
        await submit_and_discuss.edit(overwrites=regular_perms)

        await minecraft.edit(overwrites=minecraft_perms)
        for c in minecraft.channels:
            await c.edit(sync_permissions=True)
        await mc_info.edit(overwrites=mc_info_perms)
        await mc_suggest.edit(overwrites=mc_suggest_perms)
        await mc_coder.edit(overwrites=mc_coder_perms)
        await mc_builder.edit(overwrites=mc_builder_perms)
        await mc_devs.edit(overwrites=mc_devs_perms)
        await mc_mods.edit(overwrites=mc_mods_perms)
        await mc_dev_room.edit(overwrites=mc_devs_perms)

        await voice_channels.edit(overwrites=regular_perms)
        for c in minecraft.channels:
            await c.edit(sync_permissions=True)
        await nightbot.edit(overwrites=elevated_perms)

        await tahiti_text.edit(overwrites=tahiti_perms)
        await tahiti.edit(overwrites=tahiti_perms)

    # @command('rimraf')
    # @doc.hidden
    # async def rimraf(self, ctx: Circumstances):
    #     guild: Guild = ctx.guild
    #     if guild.id == facts.GUILD_ID:
    #         raise ValueError
    #     for role in guild.roles:
    #         with suppress(Exception):
    #             await role.delete()
    #     for channel in guild.channels:
    #         with suppress(Exception):
    #             await channel.delete()
    #     await ctx.send('Done.')
