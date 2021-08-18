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
from contextlib import suppress
from typing import Optional, TypedDict, Union
from urllib.parse import parse_qs, urlsplit

import inflect
from discord import (AllowedMentions, Emoji, File, Guild, HTTPException,
                     Member, Message, PartialEmoji, PartialMessage,
                     RawBulkMessageDeleteEvent, RawMessageDeleteEvent,
                     RawReactionActionEvent, Role, TextChannel)
from discord.ext.commands import BucketType, MissingAnyRole, group
from django.core.cache import caches
from django.utils.datastructures import MultiValueDict
from more_itertools import first

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.autodoc import NotAcceptable
from ts2.discord.utils.async_ import async_get, async_list
from ts2.discord.utils.common import (Embed2, EmbedPagination, a, chapterize,
                                      code, pre, strong, tag, tag_literal,
                                      timestamp, urlqueryset, utcnow)

from .models import SuggestionChannel

EmoteType = Union[Emoji, PartialEmoji, str]

inflection = inflect.engine()
RE_URL = re.compile(r'https?://\S*(\.\S+)+\S*')


class SubmissionInfo(TypedDict):
    linked_id: int
    author_id: int
    attrib_id: Optional[int]


_Submission = tuple[Embed2, SubmissionInfo]


class Poll(
    Gear, name='Poll', order=20,
    description='Suggestions & polls',
):
    _CACHE_VERSION = 2
    _CACHE_TTL = 604800

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sequential = asyncio.Lock()
        self._cache = caches['discord']
        self._invalid: set[int] = set()

    async def list_suggest_channels(self, guild: Guild) -> str:
        channels = {c.id: c for c in guild.channels}
        q = SuggestionChannel.objects.filter(channel_id__in=channels)
        lines = []
        targets = sorted((
            (guild.get_channel(c.channel_id), c)
            for c in await async_list(q)
        ), key=lambda t: t[0].position)
        for ch, c in targets:
            c: SuggestionChannel
            lines.append(f'\n{tag(channels[c.channel_id])} {c.description}')
        return '\n'.join(lines).strip()

    async def send_channel_list(self, ctx: Circumstances):
        channel_list = await self.list_suggest_channels(ctx.guild)
        if not channel_list:
            channel_list = '(no suggest channels)'
        help_text = (
            f'To make a suggestion, call {code("suggest")},'
            ' followed by the suggestion channel,'
            ' followed by the content of your submission, e.g.: '
            f'{pre("suggest #discord-suggestions Enable threads")}'
            ' To upload images/files, upload it together with the command call.'
            '\nThe submission will include a "permalink," which you can use to'
            ' edit or delete your suggestion. For example, to edit your suggestion,'
            ' copy the link, then:'
            f'{pre("suggest edit (paste link here) (updated suggestion)")}'
        )
        channel_lists = chapterize(channel_list, 1280, linebreak='newline')
        channel_lists = [f'{strong("Channels")}\n{channels}'
                         for channels in channel_lists]
        base = Embed2().decorated(ctx.guild)
        pages = [base.set_description(description=description)
                 for description in [help_text, *channel_lists]]
        pagination = EmbedPagination(pages, 'Suggestion channels')
        return await (ctx.response(ctx, embed=pagination).deleter()
                      .responder(pagination.with_context(ctx)).run())

    async def get_channel_or_404(self, ctx: Circumstances, channel: TextChannel):
        channels = [c.id for c in ctx.guild.channels]
        suggests = SuggestionChannel.objects.filter(channel_id__in=channels)
        try:
            suggest: SuggestionChannel = await async_get(suggests, channel_id=channel.id)
        except SuggestionChannel.DoesNotExist:
            raise NotAcceptable(f'{tag(channel)} is not a suggestion channel.')
        else:
            return suggest

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
            idx = len(embed.fields)
            value = line
        return embed.set_field_at(idx, name=key, value=value, inline=inline)

    def is_arbiter_in(self, target: SuggestionChannel, member: Member) -> bool:
        roles: list[Role] = member.roles
        return {r.id for r in roles} & set(target.arbiters)

    def get_text(self, target: SuggestionChannel, content: str) -> str:
        if target.requires_text and not content:
            raise NotAcceptable((f'Submissions to {tag_literal("channel", target.channel_id)}'
                                 ' must contain text description.'))
        return content

    async def get_files(self, target: SuggestionChannel, msg: Message) -> list[File]:
        min_uploads = target.requires_uploads
        if min_uploads and len(msg.attachments) < min_uploads:
            err = (f'Submissions to {tag(msg.channel)} require'
                   f' uploading at least {min_uploads}'
                   f' {inflection.plural_noun("file", min_uploads)}.')
            raise NotAcceptable(err)
        return await asyncio.gather(*[att.to_file() for att in msg.attachments])

    def get_links(self, target: SuggestionChannel, content: str) -> list[str]:
        min_links = target.requires_links
        if min_links:
            links = [m.group(0) for m in RE_URL.finditer(content)]
            if len(links) < min_links:
                err = (f'Submissions to {tag_literal("channel", target.channel_id)}'
                       f' must include at least {min_links}'
                       f' {inflection.plural_noun("link", min_links)}.')
                raise NotAcceptable(err)
            return links
        else:
            return []

    def get_preamble(
        self, target: SuggestionChannel,
        author_id: int, links: list[str],
    ) -> str:
        prefix = f'{target.title} submitted by {tag_literal("member", author_id)}:'
        return '\n'.join([prefix, *links])

    def build_return_url(
        self, src: str,
        author: Member,
        linked: Message,
    ) -> tuple[str, SubmissionInfo]:
        info = {
            'linked_id': linked.id,
            'author_id': author.id,
        }
        url = urlqueryset(src, type=f'{self.app_label}.suggestion', **info)
        return url, info

    async def add_reactions(self, target: SuggestionChannel, msg: Message):
        emotes = [target.upvote, target.downvote]
        for e in target.reactions_cleaned:
            emotes.append(e)
        for e in filter(None, emotes):
            try:
                await msg.add_reaction(e)
            except Exception:
                pass

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
            info['author_id'] = int(params['author_id'])
            info['linked_id'] = int(params['linked_id'])
        except (TypeError, ValueError, KeyError):
            return
        for key in ('attrib_id',):
            try:
                info[key] = int(params[key])
            except (TypeError, ValueError, KeyError):
                info[key] = None
        return info

    def parse_submission(self, msg: Message) -> _Submission:
        if msg.author != self.bot.user:
            raise NotSuggestion(msg)
        embed = first(msg.embeds, None)
        if not embed:
            raise NotSuggestion(msg)
        info = self.parse_return_url(embed)
        if not info:
            raise NotSuggestion(msg)
        embed = Embed2.upgrade(embed)
        return embed, info

    def get_cache_key(self, msg_id: int):
        return f'{__name__}:{self.app_label}:suggestion:{msg_id}'

    def cache_submission(self, msg_id: int, embed: Embed2, info: SubmissionInfo):
        key = self.get_cache_key(msg_id)
        self._cache.set(key, (embed, info), timeout=self._CACHE_TTL, version=self._CACHE_VERSION)

    def invalidate_submission(self, msg_id: int):
        key = self.get_cache_key(msg_id)
        self._cache.delete(key, version=self._CACHE_VERSION)

    def get_cached_submission(self, msg_id: int) -> Union[tuple[None, None], _Submission]:
        key = self.get_cache_key(msg_id)
        return self._cache.get(key, (None, None), self._CACHE_VERSION)

    async def fetch_submission(self, msg: Union[Message, PartialMessage]):
        embed: Embed2
        info: SubmissionInfo
        msg_id = msg.id
        if msg_id in self._invalid:
            raise NotSuggestion(msg)
        channel = msg.channel
        embed, info = self.get_cached_submission(msg_id)
        if not embed:
            if isinstance(msg, PartialMessage):
                msg: Message = await channel.fetch_message(msg_id)
            try:
                embed, info = self.parse_submission(msg)
            except NotSuggestion:
                self._invalid.add(msg_id)
                raise
            self.cache_submission(msg_id, embed, info)
        return embed, info

    async def update_submission(
        self, original: Union[Message, PartialMessage],
        embed: Embed2, info: SubmissionInfo,
        *, body: Optional[str] = None,
        linked: Optional[str] = None,
        status: Optional[str] = None,
        comment: Optional[str] = None,
        edited: Optional[str] = None,
        author: Optional[Member] = None,
    ):
        channel: TextChannel = original.channel
        updated = embed
        if status:
            updated = self.field_setdefault(updated, 'Response', status)
        if comment:
            updated = self.field_setdefault(updated, 'Comment', comment)
        if edited:
            updated = self.field_setdefault(updated, 'Edited', edited)
        if body:
            updated = updated.set_description(body)
        if author:
            updated = updated.personalized(author, url=embed.author.url)
        if updated is not embed:
            with suppress(HTTPException):
                await original.edit(embed=updated)
                self.cache_submission(original.id, updated, info)
        if linked:
            linked_msg = channel.get_partial_message(info['linked_id'])
            with suppress(HTTPException):
                await linked_msg.edit(content=linked)

    async def respond(self, ctx: Circumstances, content: str):
        return (await ctx.response(ctx, content=content)
                .reply().autodelete(20).run())

    @group('suggest', case_insensitive=True, invoke_without_command=True)
    @doc.description('Make a suggestion.')
    @doc.argument('category', 'The suggestion channel to use.',
                  node='[suggest channel]', signature='[channel]')
    @doc.argument('suggestion', 'Your suggestion here.')
    @doc.cooldown(1, 5, BucketType.member)
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Show a list of all suggestion channels.')
    @doc.invocation(('category', 'suggestion'), 'Submit a new suggestion.')
    async def suggest(
        self, ctx: Circumstances,
        category: Optional[Union[TextChannel, str]],
        *, suggestion: str = '',
    ):
        if category is None:
            return await self.send_channel_list(ctx)

        if not isinstance(category, TextChannel):
            raise NotAcceptable(f'No such channel {category}.')

        if not category.permissions_for(ctx.author).read_messages:
            raise NotAcceptable((f'You cannot submit to {tag(category)} because'
                                 ' the channel is not visible to you.'))

        target = await self.get_channel_or_404(ctx, category)

        if target.requires_text and not suggestion:
            raise NotAcceptable(f'Submissions to {tag(category)} must contain text description.')

        msg = ctx.message
        suggestion = self.get_text(target, suggestion)
        files = await self.get_files(target, msg)
        links = self.get_links(target, suggestion)

        async with self._sequential, ctx.typing():

            kwargs = {'allowed_mentions': AllowedMentions.none()}
            content = self.get_preamble(target, ctx.author.id, links)
            kwargs['content'] = content
            kwargs['files'] = files or None
            associated: Message = await category.send(**kwargs)

            src = ctx.message.jump_url
            author = ctx.author
            return_url, info = self.build_return_url(src, author, associated)
            submission = (
                Embed2(title=target.title or 'Suggestion',
                       description=suggestion or None)
                .set_timestamp(ctx.timestamp)
                .personalized(ctx.author, url=return_url)
            )
            res: Message = await category.send(embed=submission)

        referrer = a(strong('Permalink'), res.jump_url)
        postsubmit = submission.add_field(name='Reference', value=referrer, inline=False)
        self.cache_submission(res.id, postsubmit, info)

        await res.edit(embed=postsubmit)
        await self.add_reactions(target, res)
        await self.respond(ctx, 'Thank you for the suggestion!')

    @suggest.command('delete', aliases=('remove', 'del', 'rm'))
    @doc.description('Delete a suggestion.')
    @doc.argument('suggestion', (
        'The message containing your submission'
        ' (copy the permalink included in the message).'
    ))
    async def suggest_delete(self, ctx: Circumstances, suggestion: Message):
        category: TextChannel = suggestion.channel
        embed, info = await self.fetch_submission(suggestion)
        author = ctx.author
        if author.id != info['author_id'] and author.id != info.get('attrib_id'):
            raise NotAcceptable("You cannot delete someone else's suggestion.")
        associated = category.get_partial_message(info['linked_id'])
        await associated.delete(delay=0)
        await suggestion.delete(delay=0)
        await self.respond(ctx, f'Deleted suggestion {code(suggestion.id)}')

    @suggest.command('edit', aliased=('update', 'change', 'set'))
    @doc.description('Edit a suggestion.')
    @doc.argument('suggestion', (
        'The message containing your submission'
        ' (copy the permalink included in the message).'
    ))
    @doc.argument('content', (
        'The updated submission; replaces the original'
        ' text content of your suggestion.'
    ))
    @doc.use_syntax_whitelist
    @doc.invocation(('suggestion', 'content'), (
        'Replace the suggestion content;'
        ' note that it is not possible'
        ' to change the uploaded files'
        ' if there are any.'
    ))
    async def suggest_edit(
        self, ctx: Circumstances,
        suggestion: Message,
        *, content: str = '',
    ):
        embed, info = await self.fetch_submission(suggestion)
        author = ctx.author
        if author.id != info['author_id'] and author.id != info.get('attrib_id'):
            raise NotAcceptable("You cannot edit someone else's suggestion.")

        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)

        content = self.get_text(target, content)
        links = self.get_links(target, content)
        preamble = self.get_preamble(target, info['author_id'], links)
        edited = f'{tag(ctx.author)} {timestamp(ctx.timestamp, "relative")}'
        await self.update_submission(suggestion, embed, info, body=content,
                                     linked=preamble, edited=edited)

        await self.respond(ctx, f'Edited suggestion {code(suggestion.id)}')

    @suggest.command('comment', aliases=('review',))
    @doc.description('Add a comment to a suggestion.')
    @doc.argument('suggestion', (
        'The message containing the submission'
        ' (copy the permalink included in the message).'
    ))
    @doc.argument('comment', 'The comment to add.')
    @doc.restriction(None, (
        'Only members designated as "arbiters"'
        ' (who can add responses via reactions)'
        ' can post comments.'
    ))
    @doc.use_syntax_whitelist
    @doc.invocation(('suggestion', 'comment'), None)
    async def comment(
        self, ctx: Circumstances,
        suggestion: Message, *, comment: str,
    ):
        if not comment:
            raise NotAcceptable('Comment must not be empty.')

        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)
        if not self.is_arbiter_in(target, ctx.author):
            raise MissingAnyRole(target.arbiters)

        embed, info = await self.fetch_submission(suggestion)
        comment = f'{tag(ctx.author)} {timestamp(ctx.timestamp, "relative")}: {comment}'
        await self.update_submission(suggestion, embed, info, comment=comment)

        await self.respond(ctx, f'Comment added to suggestion {code(suggestion.id)}')

    @suggest.command('credit', aliases=('attrib',))
    @doc.description('Attribute a submission to someone else.')
    @doc.argument('suggestion', (
        'The message containing the submission'
        ' (copy the permalink included in the message).'
    ))
    @doc.argument('member', 'The member you would like to credit the suggestion to.')
    @doc.restriction(None, 'You can only change the attribution of a suggestion you submitted.')
    async def suggest_credit(
        self, ctx: Circumstances,
        suggestion: Message,
        member: Member,
    ):
        embed, info = await self.fetch_submission(suggestion)
        if ctx.author.id != info['author_id']:
            raise NotAcceptable('You can only change the attribution of a suggestion you submitted.')

        edited = f'{tag(ctx.author)} {timestamp(ctx.timestamp, "relative")}'
        await self.update_submission(suggestion, embed, info, author=member, edited=edited)

        await self.respond(ctx, f'Updated suggestion {code(suggestion.id)}')

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
        text = target.reactions_cleaned.get(emote)
        if text is None:
            return

        if not self.is_arbiter_in(target, ev.member):
            return

        msg_id = ev.message_id
        msg = channel.get_partial_message(msg_id)
        try:
            embed, info = await self.fetch_submission(msg)
        except NotSuggestion:
            self._invalid.add(msg_id)
            return

        if text:
            text = f'{emote} {strong(text)}'
        else:
            text = emote
        status = (f'{text} - {tag(ev.member)}'
                  f' {timestamp(utcnow(), "relative")}')

        await self.update_submission(msg, embed, info, status=status)

    async def delete_linked_msg(self, msg_id: int, channel: TextChannel):
        if msg_id in self._invalid:
            return
        self._invalid.add(msg_id)
        embed, info = self.get_cached_submission(msg_id)
        if embed is None:
            return
        linked = channel.get_partial_message(info['linked_id'])
        self._invalid.add(linked.id)
        await linked.delete(delay=0)
        self.invalidate_submission(msg_id)

    @Gear.listener('on_raw_message_delete')
    async def on_delete(self, ev: RawMessageDeleteEvent):
        channel: TextChannel = self.bot.get_channel(ev.channel_id)
        if not channel:
            return
        await self.delete_linked_msg(ev.message_id, channel)

    @Gear.listener('on_raw_bulk_message_delete')
    async def on_bulk_delete(self, ev: RawBulkMessageDeleteEvent):
        channel: TextChannel = self.bot.get_channel(ev.channel_id)
        if not channel:
            return
        await asyncio.gather(*[
            self.delete_linked_msg(id_, channel)
            for id_ in ev.message_ids
        ])


class NotSuggestion(NotAcceptable):
    def __init__(self, msg: Union[Message, PartialMessage], *args):
        link = a(f'Message {code(msg.id)}')
        message = f'{link} is not a submission.'
        super().__init__(message, *args)


class Invalidate(Exception):
    pass
