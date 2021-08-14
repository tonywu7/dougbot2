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
from pathlib import Path
from typing import Optional, TypedDict, Union
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import inflect
from discord import (AllowedMentions, Emoji, Guild, Member, Message,
                     PartialEmoji, RawReactionActionEvent, Role, TextChannel)
from discord.ext.commands import command
from more_itertools import first

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.utils.async_ import async_get, async_list
from ts2.discord.utils.common import Embed2, strong, tag, timestamp, utcnow

from .models import SuggestionChannel

EmoteType = Union[Emoji, PartialEmoji, str]

inflection = inflect.engine()
RE_URL = re.compile(r'https?://\S*(\.\S+)+\S*')


class SubmissionData(TypedDict):
    message_id: int
    author_id: int
    linked_msgs: list[int]


class Poll(
    Gear, name='Poll', order=20,
    description='Suggestions & polls',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sequential = asyncio.Lock()

    @Gear.listener('on_raw_reaction_add')
    async def on_reaction(self, ev: RawReactionActionEvent):
        if not ev.member:
            return
        if ev.member == self.bot.user:
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
        message: Message = await channel.get_partial_message(ev.message_id).fetch()
        if message.author != self.bot.user:
            return
        await self.append_status(message, ev.member, emote, status)

    async def list_suggest_channels(self, guild: Guild) -> str:
        channels = {c.id: c for c in guild.channels}
        q = SuggestionChannel.objects.filter(channel_id__in=channels)
        lines = []
        for c in await async_list(q):
            c: SuggestionChannel
            lines.append(tag(channels[c.channel_id]))
            if c.description:
                lines.append(c.description)
        return '\n'.join(lines).strip()

    async def get_channel_or_404(self, ctx: Circumstances, channel: TextChannel):
        channels = [c.id for c in ctx.guild.channels]
        suggests = SuggestionChannel.objects.filter(channel_id__in=channels)
        try:
            suggest: SuggestionChannel = await async_get(suggests, channel_id=channel.id)
        except SuggestionChannel.DoesNotExist:
            raise doc.NotAcceptable((f'{tag(channel)} is not a suggestion channel.'))
        else:
            return suggest

    def build_return_url(self, ctx: Circumstances, linked: list[Message]) -> str:
        split = urlsplit(ctx.message.jump_url)
        params = {'author': ctx.author.id,
                  'type': f'{self.app_label}.suggestion'}
        if linked:
            linked_ids = [msg.id for msg in linked]
            params['linked'] = ','.join(str(id_) for id_ in linked_ids)
        query = urlencode(params)
        return urlunsplit((*split[:3], query, *split[4:]))

    def parse_return_url(self, embed: Embed2) -> Optional[SubmissionData]:
        url = embed.author and embed.author.url
        if not isinstance(url, str):
            return
        split = urlsplit(url)
        params = parse_qs(split.query)
        if params.get('type', [None])[0] != f'{self.app_label}.suggestion':
            return
        info: SubmissionData = {}
        try:
            info['message_id'] = int(Path(split.path).parts[-1])
        except (IndexError, ValueError):
            return
        try:
            info['author_id'] = int(params.get('author')[0])
        except TypeError:
            return
        try:
            linked = params.get('linked')[0]
            if linked:
                info['linked_msgs'] = [int(idx) for idx in linked.split(',')]
        except (TypeError, ValueError, AttributeError, IndexError):
            info['linked_msgs'] = []
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

    async def append_status(
        self, msg: Message, member: Member,
        emote: str, status: str,
    ):
        embed: Embed2 = first(msg.embeds, None)
        if not embed:
            return
        embed = Embed2.convert_embed(embed)
        info = self.parse_return_url(embed)
        if not info:
            return
        if status:
            status = f'{emote} {strong(status)}'
        else:
            status = emote
        entry = (
            f'{status} - {tag(member)},'
            f' {timestamp(utcnow(), "relative")}'
        )
        for idx, field in enumerate(embed.fields):
            if field.name == 'Responses':
                record = f'{field.value}\n{entry}'
                break
        else:
            idx = 0
            record = entry
        embed = embed.set_field_at(idx, name='Responses', value=record, inline=False)
        await msg.edit(embed=embed)

    @command('suggest')
    @doc.description('Make a suggestion.')
    @doc.argument('category', 'The suggestion channel to use.')
    @doc.argument('suggestion', 'Your suggestion here.')
    async def suggest(
        self, ctx: Circumstances,
        category: Optional[Union[TextChannel, str]],
        *, suggestion: str = '',
    ):
        if category is None:
            channel_list = await self.list_suggest_channels(ctx.guild)
            if not channel_list:
                channel_list = '(no suggest channels)'
            res = (Embed2(title='Suggestion channels', description=channel_list)
                   .decorated(ctx.guild))
            return await ctx.response(ctx, embed=res).reply().deleter().run()

        if not isinstance(category, TextChannel):
            raise doc.NotAcceptable(f'No such channel {category}.')

        target = await self.get_channel_or_404(ctx, category)

        if target.requires_text and not suggestion:
            raise doc.NotAcceptable((f'Submissions to {tag(category)} must'
                                     ' contain text description.'))

        msg = ctx.message

        min_uploads = target.requires_uploads
        if min_uploads and len(msg.attachments) < min_uploads:
            err = (f'Submissions to {tag(category)} require'
                   f' uploading at least {min_uploads}'
                   f' {inflection.plural_noun("file", min_uploads)}.')
            raise doc.NotAcceptable(err)
        files = await asyncio.gather(*[att.to_file() for att in msg.attachments])

        min_links = target.requires_links
        if min_links:
            links = [m.group(0) for m in RE_URL.finditer(msg.content)]
            if len(links) < min_links:
                err = (f'Submissions to {tag(category)} must include'
                       f' at least {min_links}'
                       f' {inflection.plural_noun("link", min_links)}.')
                raise doc.NotAcceptable(err)
            extracted_links = '\n'.join(links)
        else:
            extracted_links = None

        associated: list[Message] = []

        async with self._sequential, ctx.typing():

            prefix = f'{target.title} by {tag(ctx.author)}'
            mention_none = AllowedMentions.none()

            if files:
                upload = await category.send(
                    content=prefix, files=files,
                    allowed_mentions=mention_none,
                )
                associated.append(upload)

            if extracted_links:
                resources = await category.send(
                    content=f'{prefix}\n{extracted_links}',
                    allowed_mentions=mention_none,
                )
                associated.append(resources)

            return_url = self.build_return_url(ctx, associated)
            if associated:
                ref = associated[0].to_reference()
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
