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
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Optional, TypedDict, Union
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import asyncstdlib as astdlib
import inflect
from discord import (AllowedMentions, Emoji, File, Guild, HTTPException,
                     Member, Message, PartialEmoji, RawReactionActionEvent,
                     Role, TextChannel)
from discord.ext.commands import BucketType, MissingAnyRole, group
from django.utils.datastructures import MultiValueDict
from more_itertools import first

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.autodoc import NotAcceptable
from ts2.discord.utils.async_ import async_get, async_list
from ts2.discord.utils.common import (Embed2, EmbedPagination, a, blockquote,
                                      chapterize, code, pre, strong, tag,
                                      tag_literal, timestamp, urlqueryset,
                                      utcnow)

from .models import SuggestionChannel

EmoteType = Union[Emoji, PartialEmoji, str]

inflection = inflect.engine()
RE_URL = re.compile(r'https?://\S*(\.\S+)+\S*')


class SubmissionInfo(TypedDict):
    message_id: int
    linked_id: int
    author_id: int
    attrib_id: Optional[int]


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
        help_text = (
            f'To make a suggestion, call {code("suggest")},'
            ' followed by the suggestion channel,'
            ' followed by the content of your submission, e.g.: '
            f'{pre("suggest #discord-suggestions Enable threads")}'
            ' To upload images/files, upload it together with the command call.'
            '\nThe submission will include a permalink, which you can use to '
            'edit or delete your suggestion, e.g.:'
            f'{pre("suggest edit [link] Updated suggestion")}'
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
        author: Member, links: list[str],
    ) -> str:
        prefix = f'{target.title} submitted by {tag(author)}:'
        return '\n'.join([prefix, *links])

    def build_return_url(self, ctx: Circumstances, linked: Message) -> str:
        split = urlsplit(ctx.message.jump_url)
        params = {'type': f'{self.app_label}.suggestion',
                  'author_id': ctx.author.id,
                  'linked_id': linked.id}
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
            idx = len(embed.fields)
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

    def ensure_submission(self, suggestion: Message):
        try:
            return self.parse_submission(suggestion)
        except NotSuggestion:
            raise NotAcceptable(f'That {a("message", suggestion.jump_url)} is not a submission.')

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

    async def fetch_associated(
        self, channel: TextChannel,
        info: SubmissionInfo,
    ) -> Optional[Message]:
        with suppress(HTTPException):
            return await self.fetch_message(info['linked_id'], channel)

    async def update_submission(
        self, original: Message,
        *, status: Optional[str] = None,
        comment: Optional[str] = None,
    ):
        embed, info = self.parse_submission(original)
        updated = embed
        if status:
            updated = self.field_setdefault(updated, 'Responses', status)
        if comment:
            updated = self.field_setdefault(updated, 'Comment', comment)
        if updated is embed:
            return
        await original.edit(embed=updated)

    @group('suggest', invoke_without_command=True)
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

        target = await self.get_channel_or_404(ctx, category)

        if target.requires_text and not suggestion:
            raise NotAcceptable(f'Submissions to {tag(category)} must contain text description.')

        msg = ctx.message
        suggestion = self.get_text(target, suggestion)
        files = await self.get_files(target, msg)
        links = self.get_links(target, suggestion)

        async with self._sequential, ctx.typing():

            kwargs = {'allowed_mentions': AllowedMentions.none()}
            content = self.get_preamble(target, ctx.author, links)
            kwargs['content'] = content
            kwargs['files'] = files or None
            associated: Message = await category.send(**kwargs)

            return_url = self.build_return_url(ctx, associated)
            submission = (
                Embed2(title=target.title or 'Suggestion',
                       description=suggestion or None)
                .set_timestamp(ctx.timestamp)
                .personalized(ctx.author, url=return_url)
            )
            res: Message = await category.send(embed=submission)

        referrer = a(strong('Permalink'), res.jump_url)
        postsubmit = submission.add_field(name='Reference', value=referrer, inline=False)
        await res.edit(embed=postsubmit)
        await self.add_reactions(target, res)
        (await ctx.response(ctx, content='Thank you for the suggestion!')
         .reply().autodelete(20).run())

    @suggest.command('delete', aliases=('remove', 'del', 'rm'))
    @doc.description('Delete a suggestion.')
    @doc.argument('suggestion', (
        'The message containing your submission'
        ' (copy the permalink included in the message).'
    ))
    async def suggest_delete(self, ctx: Circumstances, suggestion: Message):
        embed, info = self.ensure_submission(suggestion)
        author = ctx.author
        if author.id != info['author_id'] and author.id != info['attrib_id']:
            raise NotAcceptable("You cannot delete someone else's suggestion.")
        associated = await self.fetch_associated(suggestion.channel, info)
        if associated:
            await associated.delete(delay=0)
        await suggestion.delete(delay=0)
        return (await ctx.response(ctx, content=f'Deleted suggestion {code(suggestion.id)}.')
                .reply().autodelete(20).run())

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
        embed, info = self.ensure_submission(suggestion)
        author = ctx.author
        if author.id != info['author_id'] and author.id != info['attrib_id']:
            raise NotAcceptable("You cannot edit someone else's suggestion.")

        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)

        content = self.get_text(target, content)
        links = self.get_links(target, content)

        with self._cache_message(suggestion):
            await self.fetch_message(suggestion.id, category)

        associated = await self.fetch_associated(category, info)
        if associated:
            preamble = self.get_preamble(target, ctx.author, links)
            await associated.edit(content=preamble)

        submission = embed.set_description(content)
        record = f'{tag(ctx.author)} {timestamp(ctx.timestamp, "relative")}'
        submission = self.field_setdefault(submission, 'Edited', record)
        await suggestion.edit(embed=submission)
        return (await ctx.response(ctx, content=f'Edited suggestion {code(suggestion.id)}.')
                .reply().autodelete(20).run())

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

        comment = f'{tag(ctx.author)} {timestamp(ctx.timestamp, "relative")}: {comment}'
        try:
            await self.update_submission(suggestion, comment=comment)
        except NotSuggestion:
            raise NotAcceptable(f'That {a("message", suggestion.jump_url)} is not a submission.')
        return (await ctx.response(ctx, content=f'Comment added to suggestion {code(suggestion.id)}.')
                .reply().autodelete(20).run())

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
        embed, info = self.ensure_submission(suggestion)
        if ctx.author.id != info['author_id']:
            raise NotAcceptable('You can only change the attribution of a suggestion you submitted.')
        embed = embed.personalized(member, url=urlqueryset(embed.author.url, attrib_id=member.id))
        await suggestion.edit(embed=embed)
        return (await ctx.response(ctx, content=f'Updated suggestion {code(suggestion.id)}.')
                .reply().autodelete(20).run())

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

        if not self.is_arbiter_in(target, ev.member):
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
