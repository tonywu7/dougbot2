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

import asyncio
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, TypedDict, Union
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import asyncstdlib as astdlib
import inflect
from discord import (AllowedMentions, Emoji, File, Guild, HTTPException,
                     Member, Message, PartialEmoji, RawReactionActionEvent,
                     Role, TextChannel)
from discord.ext.commands import BucketType, group
from django.utils.datastructures import MultiValueDict
from more_itertools import first

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.utils.async_ import async_get, async_list
from ts2.discord.utils.common import (Embed2, blockquote, strong, tag,
                                      tag_literal, timestamp, utcnow)

from .models import SuggestionChannel

EmoteType = Union[Emoji, PartialEmoji, str]

inflection = inflect.engine()
RE_URL = re.compile(r'https?://\S*(\.\S+)+\S*')


class SubmissionInfo(TypedDict):
    message_id: int
    author_id: int
    attrib_id: Optional[int]
    links: Optional[int]
    files: Optional[int]


class SubmissionAttachments(TypedDict):
    links: Optional[Message]
    files: Optional[Message]


class Poll(
    Gear, name='Poll', order=20,
    description='Suggestions & polls',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sequential = asyncio.Lock()
        self._invalid: set[int] = set()

    async def list_suggest_channels(self, guild: Guild) -> str:
        channels = {c.id: c for c in guild.channels}
        q = SuggestionChannel.objects.filter(channel_id__in=channels)
        lines = []
        for c in await async_list(q):
            c: SuggestionChannel
            lines.append(tag(channels[c.channel_id]))
            if c.description:
                lines.append(blockquote(c.description))
        return '\n'.join(lines).strip()

    async def send_channel_list(self, ctx: Circumstances):
        channel_list = await self.list_suggest_channels(ctx.guild)
        if not channel_list:
            channel_list = '(no suggest channels)'
        res = (Embed2(title='Suggestion channels', description=channel_list)
               .decorated(ctx.guild))
        return await ctx.response(ctx, embed=res).reply().deleter().run()

    async def get_channel_or_404(self, ctx: Circumstances, channel: TextChannel):
        channels = [c.id for c in ctx.guild.channels]
        suggests = SuggestionChannel.objects.filter(channel_id__in=channels)
        try:
            suggest: SuggestionChannel = await async_get(suggests, channel_id=channel.id)
        except SuggestionChannel.DoesNotExist:
            raise doc.NotAcceptable((f'{tag(channel)} is not a suggestion channel.'))
        else:
            return suggest

    async def get_files(self, target: SuggestionChannel, msg: Message) -> list[File]:
        min_uploads = target.requires_uploads
        if min_uploads and len(msg.attachments) < min_uploads:
            err = (f'Submissions to {tag(msg.channel)} require'
                   f' uploading at least {min_uploads}'
                   f' {inflection.plural_noun("file", min_uploads)}.')
            raise doc.NotAcceptable(err)
        return await asyncio.gather(*[att.to_file() for att in msg.attachments])

    def get_links(self, target: SuggestionChannel, msg: Message) -> list[str]:
        min_links = target.requires_links
        if min_links:
            links = [m.group(0) for m in RE_URL.finditer(msg.content)]
            if len(links) < min_links:
                err = (f'Submissions to {tag(msg.channel)} must include'
                       f' at least {min_links}'
                       f' {inflection.plural_noun("link", min_links)}.')
                raise doc.NotAcceptable(err)
            return links
        else:
            return []

    def build_return_url(self, ctx: Circumstances, linked: dict[str, Message]) -> str:
        split = urlsplit(ctx.message.jump_url)
        params = {'author': ctx.author.id,
                  'type': f'{self.app_label}.suggestion'}
        for k, v in linked.items():
            params[k] = v.id
        query = urlencode(params)
        return urlunsplit((*split[:3], query, *split[4:]))

    def parse_return_url(self, embed: Embed2) -> Optional[SubmissionInfo]:
        url = embed.author and embed.author.url
        if not isinstance(url, str):
            return
        split = urlsplit(url)
        params = MultiValueDict(parse_qs(split.query))
        if params.get('type') != f'{self.app_label}.suggestion':
            return
        info: SubmissionInfo = {}
        try:
            info['message_id'] = int(Path(split.path).parts[-1])
            info['author_id'] = int(params['author'])
        except (TypeError, ValueError, KeyError):
            return
        for key in ('links', 'files', 'attrib_id'):
            try:
                info[key] = int(params[key])
            except (TypeError, ValueError, KeyError):
                info[key] = None
        return info

    async def add_reactions(self, target: SuggestionChannel, msg: Message):
        emotes = [target.upvote, target.downvote]
        for e in target.reactions_cleaned:
            emotes.append(e)
        for e in emotes:
            try:
                await msg.add_reaction(e)
            except Exception:
                pass

    def field_setdefault(
        self, embed: Embed2, key: str, line: str,
        *, replace=False, inline=False,
    ) -> Embed2:
        for idx, field in enumerate(embed.fields):
            if field.name == key:
                if replace:
                    value = line
                else:
                    value = f'{field.value}\n{line}'
                break
        else:
            idx = 0
            value = line
        return embed.set_field_at(idx, name=key, value=value, inline=inline)

    def parse_submission(self, msg: Message) -> tuple[Embed2, SubmissionInfo]:
        embed = first(msg.embeds, None)
        if not embed:
            raise NotSuggestion()
        info = self.parse_return_url(embed)
        if not info:
            raise NotSuggestion()
        embed = Embed2.upgrade(embed)
        return embed, info

    async def fetch_associated(self, info: SubmissionInfo) -> SubmissionAttachments:
        att: SubmissionAttachments = {}
        for k in ('links', 'files'):
            msg_id = info[k]
            if msg_id:
                try:
                    att[k] = self.fetch_message(msg_id)
                except HTTPException:
                    pass
        return att

    async def update_submission(
        self, original: Message,
        *, status: Optional[str] = None,
        comment: Optional[str] = None,
        author: Optional[Member] = None,
    ):
        embed, info = self.parse_submission(original)
        embed = Embed2.upgrade(embed)
        updated = embed
        if status:
            updated = self.field_setdefault(updated, 'Responses', status)
        if comment:
            updated = self.field_setdefault(updated, 'Comment', comment)
        if author:
            updated = (
                self.field_setdefault(
                    updated, 'Posted by',
                    tag_literal('member', info['author_id']),
                    inline=True,
                ).personalized(author, url=updated.author.url)
            )
        if updated is embed:
            return
        await original.edit(embed=updated)

    @contextmanager
    def _cache_message(self, msg: Message):
        self._passed_message = msg
        try:
            yield
        finally:
            del self._passed_message

    @astdlib.lru_cache(maxsize=65535)
    async def fetch_message(self, msg_id: int, channel: TextChannel) -> Message:
        passed = getattr(self, '_passed_message', None)
        if isinstance(passed, Message):
            return passed
        return await channel.fetch_message(msg_id)

    @group('suggest', invoke_without_command=True)
    @doc.description('Make a suggestion.')
    @doc.argument('category', 'The suggestion channel to use.')
    @doc.argument('suggestion', 'Your suggestion here.')
    @doc.cooldown(1, 5, BucketType.member)
    async def suggest(
        self, ctx: Circumstances,
        category: Optional[Union[TextChannel, str]],
        *, suggestion: str = '',
    ):
        if category is None:
            return await self.send_channel_list(ctx)

        if not isinstance(category, TextChannel):
            raise doc.NotAcceptable(f'No such channel {category}.')

        target = await self.get_channel_or_404(ctx, category)

        if target.requires_text and not suggestion:
            raise doc.NotAcceptable((f'Submissions to {tag(category)} must'
                                     ' contain text description.'))

        msg = ctx.message
        files = await self.get_files(target, msg)
        links = self.get_links(target, msg)

        associated: dict[str, Message] = {}

        async with self._sequential, ctx.typing():

            prefix = f'{target.title} by {tag(ctx.author)}'
            mention_none = AllowedMentions.none()

            if links:
                resources = await category.send(
                    content='\n'.join([prefix, *links]),
                    allowed_mentions=mention_none,
                )
                associated['links'] = resources

            if files:
                upload = await category.send(
                    content=prefix, files=files,
                    allowed_mentions=mention_none,
                )
                associated['files'] = upload

            return_url = self.build_return_url(ctx, associated)
            if associated:
                ref = first(associated.values()).to_reference()
            else:
                ref = None

            submission = (
                Embed2(title=target.title or 'Suggestion',
                       description=suggestion or None)
                .set_timestamp(ctx.timestamp)
                .personalized(ctx.author, url=return_url)
            )
            res = await category.send(embed=submission, reference=ref)

        await self.add_reactions(target, res)
        (await ctx.response(ctx, content='Thank you for the suggestion!')
         .reply(True).autodelete(20).run())

    @suggest.command('delete')
    @doc.description('Delete a suggestion.')
    @doc.argument('suggestion', (
        'The message containing your submission;'
        ' must be the one with your username on it.'
    ))
    async def suggest_delete(self, ctx: Circumstances, suggestion: Message):
        try:
            embed, info = self.parse_submission(suggestion)
        except NotSuggestion:
            raise doc.NotAcceptable(f'Message {suggestion.id} is not a submission.')
        author = ctx.author
        if author.id != info['author_id'] and author.id != info['attrib_id']:
            raise doc.NotAcceptable("You cannot delete someone else's suggestion.")
        associated = await self.fetch_associated(info)
        for msg in associated.values():
            msg: Message
            await msg.delete(delay=0)
        await suggestion.delete(delay=0)
        return (await ctx.response(ctx, content=f'Submission {suggestion.id} deleted.')
                .reply(True).autodelete(20).run())

    @Gear.listener('on_raw_reaction_add')
    async def on_reaction(self, ev: RawReactionActionEvent):
        if not ev.member:
            return
        if ev.member == self.bot.user:
            return
        if ev.message_id in self._invalid:
            return

        channel: TextChannel = self.bot.get_channel(ev.channel_id)
        if not channel:
            return
        try:
            target = await async_get(SuggestionChannel, channel_id=ev.channel_id)
        except SuggestionChannel.DoesNotExist:
            return

        target: SuggestionChannel
        emote = str(ev.emoji)
        status = target.reactions_cleaned.get(emote)
        if status is None:
            return

        roles: list[Role] = ev.member.roles
        if not {r.id for r in roles} & set(target.arbiters):
            return

        msg_id = ev.message_id
        message = await self.fetch_message(msg_id, channel)

        if (message.author != self.bot.user
                or message.flags.suppress_embeds):
            self._invalid.add(msg_id)
            return

        if status:
            status = f'{emote} {strong(status)}'
        else:
            status = emote
        entry = (f'{status} - {tag(ev.member)},'
                 f' {timestamp(utcnow(), "relative")}')

        try:
            await self.update_submission(message, status=entry)
        except NotSuggestion:
            self._invalid.add(msg_id)


class NotSuggestion(ValueError):
    pass
