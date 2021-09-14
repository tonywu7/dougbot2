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
import logging
import re
from contextlib import suppress
from datetime import datetime
from typing import Literal, Optional, TypedDict, Union
from urllib.parse import parse_qs, urlsplit

import inflect
from discord import (AllowedMentions, Emoji, File, Guild, HTTPException,
                     Member, Message, PartialEmoji, PartialMessage,
                     RawBulkMessageDeleteEvent, RawMessageDeleteEvent,
                     RawReactionActionEvent, Role, TextChannel)
from discord.ext.commands import BucketType, MissingAnyRole, group
from django.core.cache import caches
from django.utils.datastructures import MultiValueDict
from more_itertools import first, map_reduce

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances, on_error_reset_cooldown
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.autodoc import NotAcceptable
from ts2.discord.ext.common import Constant
from ts2.discord.utils.async_ import async_get, async_list
from ts2.discord.utils.common import (E, Embed2, EmbedPagination, a,
                                      assumed_utc, blockquote, chapterize,
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
    is_public: Optional[int]
    obfuscate: Optional[int]


class Ballot(TypedDict):
    emote: str
    response: str
    user_id: str
    timestamp: Union[str, datetime]


_Submission = tuple[Embed2, SubmissionInfo]


class Poll(
    Gear, name='Poll', order=20,
    description='Suggestions & polls',
):
    _CACHE_VERSION = 2
    _CACHE_TTL = 604800

    RE_BALLOT_FORMAT = re.compile((
        r'^(?P<emote>\S+) \*\*(?P<response>.*)\*\* - '
        r'<@(?P<user_id>\d+)> <t:(?P<timestamp>\d+).*>$'
    ), re.M)
    RE_OBFUSCATED = re.compile(r'\[\(anonymous\)\]\((\d+)\)')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sequential = asyncio.Lock()
        self._cache = caches['discord']
        self._invalid: set[int] = set()
        self.log = logging.getLogger('discord.poll')

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
            f'{strong("See")} {E("fast_forward")} {strong("next page")}'
            f' {strong("for a list of available suggestion channels.")}'
            f'\n\nTo make a suggestion, call {code("suggest")},'
            ' followed by the suggestion channel,'
            ' followed by the content of your submission, e.g.: '
            f'{pre("suggest #discord-suggestions Enable threads")}'
            ' To upload images/files, upload it together with the command call.'
            '\nThe submission will include a "permalink," which you can use to'
            ' edit or delete your suggestion. For example, to edit your suggestion,'
            ' copy the link, then:'
            f'{pre("suggest edit (paste link here) (updated suggestion)")}'
        )
        channel_lists = chapterize(channel_list, 1280, lambda c: c == '\n')
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

    async def reset_votes(self, target: SuggestionChannel, msg: Message):
        for e in target.reactions_cleaned:
            await msg.clear_reaction(e)

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
        for key in ('attrib_id', 'is_public', 'obfuscate'):
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

    def parse_responses(self, body: str, obfuscated: bool = False) -> list[Ballot]:
        ballots: list[Ballot] = []
        if obfuscated:
            body = self.RE_OBFUSCATED.sub(lambda m: f'<@{m.group(1)}>', body)
        for matched in self.RE_BALLOT_FORMAT.finditer(body):
            ballots.append(matched.groupdict())
        return ballots

    def build_responses(self, ballots: list[Ballot], obfuscated: bool = False) -> str:
        lines = []
        if obfuscated:
            def caster(ballot: Ballot):
                return f'[(anonymous)]({ballot["user_id"]})'
        else:
            def caster(ballot: Ballot):
                return tag_literal('member', ballot['user_id'])
        for b in ballots:
            lines.append(
                f'{b["emote"]} {strong(b["response"])}'
                f' - {caster(b)}'
                f' {timestamp(b["timestamp"], "relative")}',
            )
        return '\n'.join(lines)

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
        comment: Optional[str] = None,
        edited: Optional[str] = None,
        author: Optional[Member] = None,
        status: Optional[str] = None,
        public: Optional[bool] = None,
        obfuscate: Optional[bool] = None,
    ):
        channel: TextChannel = original.channel
        updated = embed
        info = {**info}
        if status:
            updated = self.field_setdefault(updated, 'Response', status, replace=True)
        if comment:
            updated = self.field_setdefault(updated, 'Comments', comment)
        if edited:
            updated = self.field_setdefault(updated, 'Edited', edited)
        if body:
            updated = updated.set_description(body)

        if author:
            url = updated.author.url
            if author.id != info['author_id']:
                info['attrib_id'] = author.id
                url = urlqueryset(url, attrib_id=author.id)
            updated = updated.personalized(author, url=url)

        if public is not None:
            info['is_public'] = int(public)
            url = updated.author.url
            url = urlqueryset(url, is_public=int(public))
            updated = updated.set_author_url(url)
            if public:
                indicator = strong(
                    f'{E("star")} Comments section for this submission is open.'
                    f'\nAnyone can add a comment by using the {code("suggest comment")} command.',
                )
            else:
                indicator = 'Comments section is closed.'
            updated = self.field_setdefault(updated, 'Forum', indicator, replace=True)

        if obfuscate is not None:
            info['obfuscate'] = int(obfuscate)
            url = updated.author.url
            url = urlqueryset(url, obfuscate=int(obfuscate))
            updated = updated.set_author_url(url)

        if updated is not embed:
            try:
                updated.check_oversized()
            except ValueError:
                raise NotAcceptable(
                    'This submission has reached its max content size'
                    ' and can no longer be modified.',
                )
            try:
                await original.edit(embed=updated)
            except HTTPException as e:
                self.log.warning(f'Error while setting embed: {e}', exc_info=e)
            else:
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
    @doc.cooldown(1, 60, BucketType.member)
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Show a list of all suggestion channels.')
    @doc.invocation(('category', 'suggestion'), 'Submit a new suggestion.')
    @on_error_reset_cooldown
    async def suggest(
        self, ctx: Circumstances,
        category: Optional[Union[TextChannel, str]],
        *, suggestion: str = '',
    ):
        if category is None:
            ctx.command.reset_cooldown(ctx)
            return await self.send_channel_list(ctx)

        if not isinstance(category, TextChannel):
            raise NotAcceptable(f'No such channel {category}.')

        if not category.permissions_for(ctx.author).read_messages:
            raise NotAcceptable((f'You cannot submit to {tag(category)} because'
                                 ' the channel is not visible to you.'))

        target = await self.get_channel_or_404(ctx, category)

        if target.requires_text and not suggestion:
            raise NotAcceptable((f'Submissions to {tag(category)} must contain text description:'
                                 ' what you would like to suggest?'))

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
    @doc.cooldown(1, 5, BucketType.member)
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
    @doc.use_syntax_whitelist
    @doc.invocation(('suggestion', 'comment'), None)
    @doc.cooldown(1, 60, BucketType.member)
    async def comment(
        self, ctx: Circumstances,
        suggestion: Message, *, comment: str,
    ):
        if not comment:
            raise NotAcceptable('Comment must not be empty.')

        embed, info = await self.fetch_submission(suggestion)
        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)

        is_arbiter = self.is_arbiter_in(target, ctx.author)
        is_public = info.get('is_public')

        if not is_arbiter and not is_public:
            if is_public is not None:
                link = a(f'suggestion {code(suggestion.id)}', suggestion.jump_url)
                raise NotAcceptable(f'Comments section for {link} is closed.')
            else:
                raise MissingAnyRole(target.arbiters)

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
    @doc.cooldown(1, 5, BucketType.member)
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

    @suggest.command('forum')
    @doc.description('Open up the comments section of a suggestion to everyone.')
    @doc.argument('suggestion', (
        'The message containing the submission'
        ' (copy the permalink included in the message).'
    ))
    @doc.argument('enabled', 'Whether to open or close the comments section.')
    @doc.restriction(None, 'You can only change the comment access of a suggestion you submitted.')
    @doc.cooldown(1, 5, BucketType.member)
    async def suggest_forum(
        self, ctx: Circumstances,
        suggestion: Message, enabled: bool = True,
    ):
        embed, info = await self.fetch_submission(suggestion)
        if ctx.author.id != info['author_id']:
            raise NotAcceptable('You can only change the comment access of a suggestion you submitted.')

        await self.update_submission(suggestion, embed, info, public=enabled)
        res = f'Comments section for suggestion {code(suggestion.id)} is now {strong("on" if enabled else "off")}'
        await self.respond(ctx, res)

    @suggest.command('tally')
    @doc.description('Count the votes on a suggestion.')
    @doc.argument('suggestion', 'The message containing the submission.')
    @doc.argument('anonymize', "Whether to omit vote casters' username from the report.")
    async def suggest_tally(
        self, ctx: Circumstances, suggestion: Message,
        anonymize: Optional[Constant[Literal['anonymize']]] = False,
    ):
        embed, info = await self.fetch_submission(suggestion)
        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)

        votes = {str(r.emoji): r.count - r.me for r in suggestion.reactions}
        votes = {k: votes.get(k, 0) for k in (target.upvote, target.downvote) if k}
        ballots = self.parse_responses(embed.get_field_value('Response'), info.get('obfuscate'))
        ballots = map_reduce(ballots, lambda v: f'{v["emote"]} {strong(v["response"])}',
                             lambda v: tag_literal('user', v['user_id']),
                             lambda vs: sorted(set(vs)))

        lines = []
        for k, v in votes.items():
            lines.append(f'{code(v)} {k}')
        for k, v in ballots.items():
            lines.append((f'{code(len(v))} {k}\n{blockquote(" ".join(v))}'
                          if not anonymize else f'{code(len(v))} {k}'))
        if lines:
            report = '\n'.join(lines)
        else:
            report = '(No vote casted)'

        suggested = assumed_utc(suggestion.created_at).timestamp()
        tallied = utcnow().timestamp()

        res = (embed.clear_fields()
               .add_field(name='Votes', value=report, inline=False)
               .add_field(name='Reference', value=embed.get_field_value('Reference'))
               .add_field(name='Suggested', value=timestamp(suggested, 'relative'))
               .add_field(name='Tallied', value=timestamp(tallied, 'relative'))
               .set_timestamp())
        return await ctx.response(ctx, embed=res).reply().deleter().run()

    @suggest.command('obfuscate')
    @doc.description('Toggle username omission in votes.')
    @doc.argument('suggestion', 'The message containing the submission.')
    async def suggest_obfuscate(
        self, ctx: Circumstances, suggestion: Message,
    ):
        embed, info = await self.fetch_submission(suggestion)
        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)
        obfuscated = bool(info.get('obfuscate'))
        res = self.parse_responses(embed.get_field_value('Response'), obfuscated)
        obfuscated = not obfuscated
        res = self.build_responses(res, obfuscated)
        await self.update_submission(suggestion, embed, info, status=res, obfuscate=obfuscated)
        await self.reset_votes(target, suggestion)
        await self.add_reactions(target, suggestion)
        await ctx.response(ctx).success().run()

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

        res = embed.get_field_value('Response')
        obfuscated = info.get('obfuscate')
        ballots = self.parse_responses(res, obfuscated)
        vote = {
            'emote': emote, 'response': text,
            'user_id': ev.member.id,
            'timestamp': utcnow(),
        }
        if target.voting_history:
            ballots.append(vote)
        else:
            ballots_dict = {b['user_id']: b for b in ballots}
            ballots_dict[str(ev.member.id)] = vote
            ballots = [*ballots_dict.values()]
        status = self.build_responses(ballots, obfuscated)

        try:
            await self.update_submission(msg, embed, info, status=status)
        except NotAcceptable:
            pass
        except Exception as e:
            self.log.warning(f'Error while updating reactions: {e}', exc_info=e)

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
        link = a(f'Message {code(msg.id)}', msg.jump_url)
        message = f'{link} is not a submission.'
        super().__init__(message, *args)


class Invalidate(Exception):
    pass
