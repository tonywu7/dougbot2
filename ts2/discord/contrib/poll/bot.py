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
import base64
import logging
import re
from contextlib import suppress
from datetime import datetime, timezone
from typing import Literal, Optional, Union
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import attr
import inflect
import simplejson as json
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
from ts2.discord.utils.common import (E, Embed2, EmbedField, EmbedPagination,
                                      a, assumed_utc, blockquote, chapterize,
                                      code, pre, strong, tag, tag_literal,
                                      timestamp, utcnow)

from .models import SuggestionChannel

EmoteType = Union[Emoji, PartialEmoji, str]

inflection = inflect.engine()
RE_URL = re.compile(r'https?://\S*(\.\S+)+\S*')


def _default_int(v, default=0) -> int:
    try:
        return int(v)
    except Exception:
        return 0


@attr.s(frozen=True, slots=True)
class Vote:
    user_id: int = attr.ib(converter=int)
    created: float = attr.ib(converter=float)
    emote: str = attr.ib()
    text: Optional[str] = attr.ib(default=None)


@attr.s(frozen=True, slots=True)
class Comment:
    user_id: int = attr.ib(converter=int)
    created: float = attr.ib(converter=float)
    content: str = attr.ib()


@attr.s(frozen=True, slots=True)
class EditTime:
    user_id: int = attr.ib(converter=int)
    modified: float = attr.ib(converter=float)


class Poll:

    RE_VOTE = re.compile((
        r'^(?P<emote>\S+) \*\*(?P<text>.*)\*\* - '
        r'<@(?P<user_id>\d+)> <t:(?P<created>\d+).*>$'
    ), re.MULTILINE)
    RE_EDIT_TIME = re.compile((
        r'^<@(?P<user_id>\d+)> <t:(?P<modified>\d+).*>$'
    ), re.MULTILINE)
    RE_COMMENT = re.compile((
        r'^<@(?P<user_id>\d+)> <t:(?P<created>\d+).*>:'
        r' (?P<content>.+)$'
    ), re.MULTILINE)
    RE_OBFUSCATION = re.compile(r'\[\(anonymous\)\]\((?P<id>\d+)\)')

    def __init__(
        self, content: str, choices: dict[EmoteType, Optional[str]],
        *, author: str = 'unknown', title: str = 'Poll',
    ):
        self.title = title
        self.author = author
        self.content = content
        self.choices = {**choices}

        self.origin_url: str = ''
        self.linked_msg: int = 0

        self.author_id: int = 0
        self.author_icon: str = ''
        self.attrib_id: int = 0

        self.color: int = 0
        self.created: float = utcnow().timestamp()

        self.votes: list[Vote] = []
        self.comments: list[Comment] = []
        self.edits: list[EditTime] = []

        self.single_choice = False
        self.forum = False
        self.obfuscated = False

    @classmethod
    def from_embed(cls, embed: Embed2):
        title = embed.title
        content = embed.description
        author = embed.author.name
        url = urlsplit(embed.author.url)
        config = MultiValueDict(parse_qs(url.query))
        choices = json.loads(base64.urlsafe_b64decode(config['options']).decode('utf8'))
        poll = cls(content, choices, author=author, title=title)

        poll.origin_url = urlunsplit((url.scheme, url.netloc, url.path, '', ''))
        poll.load_config(config)

        poll.load_votes(embed.get_field_value('Response'))
        poll.load_comments(embed.get_field_value('Comments'))
        poll.load_edits(embed.get_field_value('Edited'))

        if embed.timestamp:
            poll.created = assumed_utc(embed.timestamp).timestamp()
        poll.author_icon = embed.author.icon_url or ''
        poll.color = embed.color.value or poll.color

        return poll

    def __setstate__(self, state):
        self.__dict__ = state
        self.__dict__.setdefault('single_choice', False)
        self.__dict__.setdefault('forum', False)
        self.__dict__.setdefault('obfuscated', False)

    def deobfuscate(self, text: str) -> str:
        return self.RE_OBFUSCATION.sub(r'<@\g<id>>', text)

    def load_config(self, config: dict):
        self.linked_msg = _default_int(config.get('linked'))
        self.author_id = _default_int(config.get('author'))
        self.attrib_id = _default_int(config.get('attrib'))
        self.single_choice = bool(_default_int(config.get('single')))
        self.forum = bool(_default_int(config.get('forum')))
        self.obfuscated = bool(_default_int(config.get('anon')))

    def load_votes(self, text: str):
        text = self.deobfuscate(text)
        self.votes = [Vote(**v.groupdict()) for v
                      in self.RE_VOTE.finditer(text)]

    def load_comments(self, text: str):
        text = self.deobfuscate(text)
        self.comments = [Comment(**c.groupdict()) for c
                         in self.RE_COMMENT.finditer(text)]

    def load_edits(self, text: str):
        text = self.deobfuscate(text)
        self.edits = [EditTime(**e.groupdict()) for e
                      in self.RE_EDIT_TIME.finditer(text)]

    def vote(self, member: Member, option: EmoteType):
        emote = str(option)
        try:
            text = self.choices[emote]
        except KeyError:
            raise ValueError(f'Invalid option {option}')
        self.votes.append(Vote(member.id, utcnow().timestamp(), emote, text))
        if self.single_choice:
            unique_votes = {v.user_id: v for v in self.votes}
            self.votes = [*unique_votes.values()]

    def comment(self, member: Member, content: str):
        self.comments.append(Comment(member.id, utcnow().timestamp(), content))

    def edit(self, member: Member, content: str):
        self.content = content
        self.touch(member)

    def touch(self, member: Member):
        self.edits.append(EditTime(member.id, utcnow().timestamp()))

    def set_origin(self, msg: Message):
        self.origin_url = msg.jump_url

    def set_linked(self, msg: Message):
        self.linked_msg = msg.id

    def set_credit(self, member: Member):
        self.author = str(member)
        self.attrib_id = member.id
        self.author_icon = str(member.avatar_url)
        self.color = member.color.value

    def set_author(self, member: Member):
        self.set_credit(member)
        self.author_id = member.id

    def get_user_display(self, user_id: int) -> str:
        if self.obfuscated:
            return a('(anonymous)', user_id)
        else:
            return tag_literal('user', user_id)

    def get_external_links(self) -> list[str]:
        return [m.group(0) for m in RE_URL.finditer(self.content)]

    def gen_permalink(self, message: Message) -> EmbedField:
        permalink = a(strong('Permalink'), message.jump_url)
        return EmbedField('Reference', permalink, False)

    def gen_votes(self) -> EmbedField:
        lines: list[str] = []
        for v in self.votes:
            if not v.text:
                continue
            lines.append(
                f'{v.emote} {strong(v.text)}'
                f' - {self.get_user_display(v.user_id)}'
                f' {timestamp(v.created, "relative")}',
            )
        return EmbedField('Response', '\n'.join(lines), False)

    def gen_comments(self) -> EmbedField:
        lines = []
        for c in self.comments:
            lines.append(
                f'{self.get_user_display(c.user_id)}'
                f' {timestamp(c.created, "relative")}'
                f': {c.content}',
            )
        return EmbedField('Comments', '\n'.join(lines), False)

    def gen_history(self) -> EmbedField:
        lines = []
        for edit in self.edits:
            lines.append(
                f'{self.get_user_display(edit.user_id)}'
                f' {timestamp(edit.modified, "relative")}',
            )
        return EmbedField('Edited', '\n'.join(lines), False)

    def gen_forum(self) -> EmbedField:
        indicator = strong(
            f'{E("star")} Comments section for this submission is open.'
            f'\nAnyone can add a comment by using the {code("suggest comment")} command.',
        )
        return EmbedField('Forum', indicator, False)

    def to_url(self) -> str:
        params = {
            'linked': self.linked_msg,
            'author': self.author_id,
            'attrib': self.attrib_id,
            'single': int(self.single_choice),
            'forum': int(self.forum),
            'anon': int(self.obfuscated),
        }
        options = json.dumps(self.choices)
        params['options'] = base64.urlsafe_b64encode(options.encode()).decode('ascii')
        query = urlencode({k: v for k, v in params.items() if v})
        return urlunsplit((*urlsplit(self.origin_url)[:3], query, ''))

    def to_embed(self, message: Optional[Message] = None) -> Embed2:
        fields = []
        if message:
            fields.append(self.gen_permalink(message))
        if self.votes:
            fields.append(self.gen_votes())
        if self.comments:
            fields.append(self.gen_comments())
        if self.edits:
            fields.append(self.gen_history())
        if self.forum:
            fields.append(self.gen_forum())
        title = self.title or 'Poll'
        content = self.content or '(no text content)'
        return (
            Embed2(title=title, description=content, fields=fields)
            .set_author(name=self.author, url=self.to_url(), icon_url=self.author_icon)
            .set_timestamp(self.timestamp)
            .set_color(self.color)
        )

    def can_update(self, member: Member) -> bool:
        return member.id == self.author_id or member.id == self.attrib_id

    def can_delete(self, member: Member) -> bool:
        return member.id == self.author_id

    @property
    def minor_choices(self) -> list[str]:
        return [k for k, v in self.choices.items() if not v]

    @property
    def major_choices(self) -> dict[str, str]:
        return {k: v for k, v in self.choices.items() if v}

    @property
    def timestamp(self) -> datetime:
        return datetime.fromtimestamp(self.created, timezone.utc)

    def tally(self, origin: Message, hide_username: bool = False) -> Embed2:
        scores = {str(r.emoji): r.count - r.me for r in origin.reactions}
        scores = {k: scores.get(k, 0) for k in self.minor_choices}

        votes = map_reduce(
            self.votes, lambda v: f'{v.emote} {strong(v.text)}',
            lambda v: tag_literal('user', v.user_id),
            lambda vs: sorted(set(vs)),
        )

        lines = []
        for k, v in scores.items():
            lines.append(f'{code(v)} {k}')
        for k, v in votes.items():
            lines.append((f'{code(len(v))} {k}\n{blockquote(" ".join(v))}'
                          if not hide_username else f'{code(len(v))} {k}'))
        if lines:
            report = '\n'.join(lines)
        else:
            report = '(No vote casted)'

        polled = self.timestamp
        tallied = utcnow().timestamp()

        return (
            self.to_embed(origin)
            .clear_fields()
            .add_field(name='Polled', value=timestamp(polled, 'relative'))
            .add_field(name='Counted', value=timestamp(tallied, 'relative'))
            .add_field(name='Votes', value=report, inline=False)
            .set_timestamp()
        )


class Polling(
    Gear, name='Poll', order=20,
    description='Suggestions & polls',
):
    _CACHE_VERSION = 5
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

    def get_cache_key(self, msg_id: int):
        return f'{__name__}:{self.app_label}:suggestion:{msg_id}'

    def cache_submission(self, msg_id: int, poll: Poll):
        key = self.get_cache_key(msg_id)
        self._cache.set(key, poll, timeout=self._CACHE_TTL, version=self._CACHE_VERSION)

    def invalidate_submission(self, msg_id: int):
        key = self.get_cache_key(msg_id)
        self._cache.delete(key, version=self._CACHE_VERSION)

    def get_cached_submission(self, msg_id: int) -> Optional[Poll]:
        key = self.get_cache_key(msg_id)
        return self._cache.get(key, None, self._CACHE_VERSION)

    def parse_submission(self, msg: Message) -> Poll:
        if msg.author != self.bot.user:
            raise NotPoll(msg)
        embed = first(msg.embeds, None)
        if not embed:
            raise NotPoll(msg)
        embed = Embed2.upgrade(embed)
        try:
            return Poll.from_embed(embed)
        except Exception:
            raise NotPoll(msg)

    async def fetch_submission(self, msg: PartialMessage) -> Poll:
        msg_id = msg.id
        if msg_id in self._invalid:
            raise NotPoll(msg)
        channel = msg.channel
        poll = self.get_cached_submission(msg_id)
        if not poll:
            if isinstance(msg, PartialMessage):
                msg: Message = await channel.fetch_message(msg_id)
            try:
                poll = self.parse_submission(msg)
            except NotPoll:
                self._invalid.add(msg_id)
                raise
            self.cache_submission(msg_id, poll)
        return poll

    async def update_submission(self, poll: Poll, origin: PartialMessage,
                                *, linked: Optional[str] = None):
        channel: TextChannel = origin.channel
        updated = poll.to_embed(origin)
        try:
            updated.check_oversized()
        except ValueError:
            raise NotAcceptable(
                'This submission has reached its max content size'
                ' and can no longer be modified.',
            )
        try:
            await origin.edit(embed=updated)
        except HTTPException as e:
            self.log.warning(f'Error while setting embed: {e}', exc_info=e)
        else:
            self.cache_submission(origin.id, poll)

        if linked:
            linked_msg = channel.get_partial_message(poll.linked_msg)
            with suppress(HTTPException):
                await linked_msg.edit(allowed_mentions=AllowedMentions.none(),
                                      content=linked)

    def get_suggestion_text(self, target: SuggestionChannel, content: str):
        if target.requires_text and not content:
            raise NotAcceptable((
                f'Submissions to {tag_literal("channel", target.channel_id)}'
                ' must contain text description:'
                ' what you would like to suggest?'
            ))
        return content

    def get_suggestion_links(self, target: SuggestionChannel, links: list[str]):
        min_links = target.requires_links
        if min_links and len(links) < min_links:
            err = (f'Submissions to {tag_literal("channel", target.channel_id)}'
                   f' must include at least {min_links}'
                   f' {inflection.plural_noun("link", min_links)}.')
            raise NotAcceptable(err)
        return links

    async def get_suggestion_files(self, target: SuggestionChannel, msg: Message) -> list[File]:
        min_uploads = target.requires_uploads
        if min_uploads and len(msg.attachments) < min_uploads:
            err = (f'Submissions to {tag(msg.channel)} require'
                   f' uploading at least {min_uploads}'
                   f' {inflection.plural_noun("file", min_uploads)}.')
            raise NotAcceptable(err)
        return await asyncio.gather(*[att.to_file() for att in msg.attachments])

    def get_preamble(
        self, target: SuggestionChannel,
        author_id: int, links: list[str],
    ) -> str:
        prefix = f'{target.title} submitted by {tag_literal("member", author_id)}:'
        return '\n'.join([prefix, *links])

    def is_arbiter_in(self, target: SuggestionChannel, member: Member) -> bool:
        roles: list[Role] = member.roles
        return {r.id for r in roles} & set(target.arbiters)

    async def add_reactions(self, poll: Poll, msg: Message):
        for e in filter(None, poll.choices):
            with suppress(Exception):
                await msg.add_reaction(e)

    async def reset_votes(self, poll: Poll, msg: Message):
        for emote in poll.major_choices:
            with suppress(Exception):
                await msg.clear_reaction(emote)

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
            raise NotAcceptable(f'No such text channel {category}.')

        if not category.permissions_for(ctx.author).read_messages:
            raise NotAcceptable((f'You cannot submit to {tag(category)} because'
                                 ' the channel is not visible to you.'))

        target = await self.get_channel_or_404(ctx, category)
        msg = ctx.message

        suggestion = self.get_suggestion_text(target, suggestion)
        poll = Poll(suggestion, target.all_emotes, title=target.title)
        poll.set_author(ctx.author)
        poll.set_origin(msg)
        poll.single_choice = not target.voting_history

        links = self.get_suggestion_links(target, poll.get_external_links())
        files = await self.get_suggestion_files(target, msg)

        async with self._sequential, ctx.typing():

            kwargs = {'allowed_mentions': AllowedMentions.none()}
            content = self.get_preamble(target, ctx.author.id, links)
            kwargs['content'] = content
            kwargs['files'] = files or None
            linked: Message = await category.send(**kwargs)
            poll.set_linked(linked)

            submission = poll.to_embed()
            res: Message = await category.send(embed=submission)

        self.cache_submission(res.id, poll)
        await res.edit(embed=poll.to_embed(res))
        await self.add_reactions(poll, res)
        await self.respond(ctx, 'Thank you for the suggestion!')

    @suggest.command('delete', aliases=('remove', 'del', 'rm'))
    @doc.description('Delete a suggestion.')
    @doc.argument('suggestion', (
        'The message containing your submission'
        ' (copy the permalink included in the message).'
    ))
    async def suggest_delete(self, ctx: Circumstances, suggestion: Message):
        category: TextChannel = suggestion.channel
        poll = await self.fetch_submission(suggestion)
        if not poll.can_delete(ctx.author):
            raise NotAcceptable("You cannot delete someone else's suggestion.")
        associated = category.get_partial_message(poll.linked_msg)
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
        poll = await self.fetch_submission(suggestion)
        if not poll.can_update(ctx.author):
            raise NotAcceptable("You cannot edit someone else's suggestion.")

        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)

        content = self.get_suggestion_text(target, content)
        poll.edit(ctx.author, content)

        links = self.get_suggestion_links(target, poll.get_external_links())
        preamble = self.get_preamble(target, poll.author_id, links)
        await self.update_submission(poll, suggestion, linked=preamble)

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

        poll = await self.fetch_submission(suggestion)
        category = suggestion.channel
        target = await self.get_channel_or_404(ctx, category)

        is_arbiter = self.is_arbiter_in(target, ctx.author)
        is_public = poll.forum

        if not is_arbiter and not is_public:
            if is_public is not None:
                link = a(f'suggestion {code(suggestion.id)}', suggestion.jump_url)
                raise NotAcceptable(f'Comments section for {link} is closed.')
            else:
                raise MissingAnyRole(target.arbiters)

        poll.comment(ctx.author, comment)
        await self.update_submission(poll, suggestion)

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
        poll = await self.fetch_submission(suggestion)
        if not poll.can_delete(ctx.author):
            raise NotAcceptable('You can only change the attribution of a suggestion you submitted.')

        if poll.attrib_id:
            poll.touch(ctx.author)
        poll.set_credit(member)
        await self.update_submission(poll, suggestion)

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
    @doc.hidden
    async def suggest_forum(
        self, ctx: Circumstances,
        suggestion: Message, enabled: bool = True,
    ):
        poll = await self.fetch_submission(suggestion)
        if not poll.can_delete(ctx.author):
            raise NotAcceptable('You can only change the comment access of a suggestion you submitted.')
        poll.forum = enabled
        await self.update_submission(poll, suggestion)
        res = (f'Comments section for suggestion {code(suggestion.id)} is now'
               f' {strong("on" if enabled else "off")}')
        await self.respond(ctx, res)

    @suggest.command('tally')
    @doc.description('Count the votes on a suggestion.')
    @doc.argument('suggestion', 'The message containing the submission.')
    @doc.argument('anonymize', "Whether to omit vote casters' username from the report.")
    @doc.hidden
    async def suggest_tally(
        self, ctx: Circumstances, suggestion: Message,
        anonymize: Optional[Constant[Literal['anonymize']]] = False,
    ):
        poll = await self.fetch_submission(suggestion)
        res = poll.tally(suggestion, bool(anonymize))
        return await ctx.response(ctx, embed=res).deleter().run()

    @suggest.command('obfuscate')
    @doc.description('Toggle username omission in votes.')
    @doc.argument('suggestion', 'The message containing the submission.')
    @doc.hidden
    async def suggest_obfuscate(
        self, ctx: Circumstances, suggestion: Message,
    ):
        poll = await self.fetch_submission(suggestion)
        poll.obfuscated = not poll.obfuscated
        await self.update_submission(poll, suggestion)
        await self.reset_votes(poll, suggestion)
        await self.add_reactions(poll, suggestion)
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
        text = target.all_emotes.get(emote)
        if not text:
            return

        if not self.is_arbiter_in(target, ev.member):
            return

        msg_id = ev.message_id
        msg = channel.get_partial_message(msg_id)
        try:
            poll = await self.fetch_submission(msg)
        except NotPoll:
            self._invalid.add(msg_id)
            return

        try:
            poll.vote(ev.member, emote)
        except ValueError:
            return

        try:
            await self.update_submission(poll, msg)
        except NotAcceptable:
            pass
        except Exception as e:
            self.log.warning(f'Error while updating reactions: {e}', exc_info=e)

    async def delete_linked_msg(self, msg_id: int, channel: TextChannel):
        if msg_id in self._invalid:
            return
        self._invalid.add(msg_id)
        poll = self.get_cached_submission(msg_id)
        if poll is None:
            return
        linked = channel.get_partial_message(poll.linked_msg)
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

    @suggest.command('migrate')
    @doc.description('Migrate old system.')
    @doc.hidden
    async def migrate(
        self, ctx: Circumstances,
        oldest: Message,
        newest: Message,
        dryrun: bool = True,
    ):
        def parse_return_url(embed: Embed2):
            url = embed.author and embed.author.url
            if not isinstance(url, str):
                return
            split = urlsplit(url)
            params = MultiValueDict(parse_qs(split.query))
            if params.get('type') != f'{self.app_label}.suggestion':
                return
            info = {}
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
        target = await self.get_channel_or_404(ctx, oldest.channel)
        options = target.all_emotes
        updated: list[tuple[Message, Embed2]] = []
        failed: list[tuple[Message, Exception]] = []
        archive: dict[str, dict] = {}
        async with ctx.typing():
            async for msg in ctx.channel.history(after=oldest, before=newest):
                try:
                    msg: Message
                    if msg.author != ctx.bot.user:
                        continue
                    embed = first(msg.embeds, None)
                    if not embed:
                        continue
                    embed = Embed2.upgrade(embed)
                    info = parse_return_url(embed)
                    if not info:
                        continue
                    query = {
                        'linked': info['linked_id'],
                        'author': info['author_id'],
                        'attrib': info['attrib_id'] or 0,
                        'single': not target.voting_history,
                        'forum': info['is_public'] or 0,
                        'anon': info['obfuscate'] or 0,
                        'options': base64.urlsafe_b64encode(json.dumps(options).encode()).decode('ascii'),
                    }
                    url = urlunsplit((*urlsplit(embed.author.url)[:3], urlencode({k: v for k, v in query.items() if v}), ''))
                    embed = embed.set_author_url(url)
                    poll = Poll.from_embed(embed)
                    upgraded = poll.to_embed(msg)
                    assert embed.description == upgraded.description, 'content'
                    assert embed.title == upgraded.title, 'title'
                    assert embed.author.name == upgraded.author.name, 'author'
                    assert embed.timestamp.timestamp() == upgraded.timestamp.timestamp(), 'timestamp'
                    assert embed.color.value == upgraded.color.value, 'color'
                    assert upgraded.get_field_value('Reference'), 'reference'
                    for f in ('Reference', 'Response', 'Comments', 'Edited'):
                        assert embed.get_field_value(f) == upgraded.get_field_value(f), f
                    updated.append((msg, upgraded))
                    archive[str(msg.id)] = embed.to_dict()
                except Exception as e:
                    failed.append((msg, e))
            failures = '\n'.join([f'{a(i, m.jump_url)} {type(e)}: {e}' for i, (m, e) in enumerate(failed)])
            description = f'{tag(ctx.channel)}\nSuccessful {len(updated)} Failed {len(failed)}\n{failures}'
            pages = []
            for c in chapterize(description, 720, lambda c: c == '\n'):
                pages.append(Embed2(title='Migration', description=c))
            pager = EmbedPagination(pages, None)
            await ctx.response(ctx, embed=pager).responder(pager.with_context(ctx)).run()
            if updated:
                await ctx.response(ctx, embed=updated[0][1]).run()
        if dryrun:
            return
        import io
        f = io.StringIO(json.dumps(archive))
        ff = File(f, filename='archive.json')
        await ctx.send(file=ff)
        async with ctx.typing():
            import time
            ctime = time.time()
            for i, (msg, embed) in enumerate(updated, 1):
                await msg.edit(embed=embed)
                if time.time() - ctime > 5:
                    ctime = time.time()
                    await ctx.send(f'Migrated {i} of {len(updated)} embeds')
            return await ctx.send(f'Migrated {len(updated)} embeds')


class NotPoll(NotAcceptable):
    def __init__(self, msg: Union[Message, PartialMessage], *args):
        link = a(f'Message {code(msg.id)}', msg.jump_url)
        message = f'{link} is not a submission.'
        super().__init__(message, *args)


class Invalidate(Exception):
    pass
