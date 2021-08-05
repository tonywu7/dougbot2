# explanation.py
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

from __future__ import annotations

import heapq
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Literal, Optional, Union

from discord import AllowedMentions
from discord.ext.commands import BucketType, Context, errors
from discord.ext.commands.view import StringView
from discord.utils import escape_markdown

from ...utils.duckcord.color import Color2
from ...utils.duckcord.embeds import Embed2
from ...utils.markdown import code, strong, tag_literal
from . import exceptions
from .documentation import readable_perm_name
from .lang import pl_cat_predicative, pluralize

_ExceptionType = Union[type[Exception], tuple[type[Exception]]]
_ExceptionHandler = Callable[[Context, Exception], Coroutine[None, None, Union[tuple[str, float], Literal[False], None]]]

exception_handlers: list[tuple[int, str, _ExceptionType, _ExceptionHandler]] = []
exception_names: dict[_ExceptionType, str] = {}

BUCKET_DESCRIPTIONS = {
    BucketType.default: 'globally',
    BucketType.user: 'per user',
    BucketType.member: 'per user',
    BucketType.guild: 'per server',
    BucketType.channel: 'per channel',
    BucketType.category: 'per channel category',
    BucketType.role: 'per role',
}


def indicate_eol(s: StringView) -> str:
    return f'{s.buffer[:s.index + 1]} ←'


def indicate_extra_text(s: StringView) -> str:
    return f'{s.buffer[:s.index]} → {s.buffer[s.index:]} ←'


def full_invoked_with(self: Context):
    return ' '.join({**{k: True for k in self.invoked_parents},
                     self.invoked_with: True}.keys())


def explains(exc: _ExceptionType, name: Optional[str] = None, priority=0):
    """Register this function for explaining the specified Exception.

    The function must take exactly two arguments, the Context and the
    caught exception.

    The function must return a coroutine, which, when awaited, must return
        one of the following:

    - A tuple of a string and a number: the string will be the error message,
        and the number will be the number of seconds before the error message
        is autodeleted.
    - The literal False (no other falsy value accepted): the error will be
        ignored and no further handler will be checked.
    - The literal None: indicate that this function will not handle this
        exception and the logging module should keep checking other handlers.

    Setting different priorities allows you to have multiple handlers for
    the subclass and superclasses of an Exception type.

    :param exc: The type(s) of exceptions this function will handle
    :type exc: Union[type[Exception], tuple[type[Exception]]]
    :param name: A short description of this exception to be used as the title
        of the error message.
    :type name: Optional[str], optional
    :param priority: Handlers with a higher priority will be checked first
    :type priority: int, optional
    """
    if not isinstance(exc, tuple):
        exc = (exc,)

    def wrapper(f: _ExceptionHandler):
        heapq.heappush(exception_handlers, (priority, str(exc), exc, f))
        if name:
            exception_names[exc] = name
        return f
    return wrapper


async def reply_command_failure(ctx: Context, title: str, msg: str,
                                autodelete: float = 60, ping=False):
    if ping:
        allowed_mentions = AllowedMentions(everyone=False, roles=False, users=False, replied_user=True)
    else:
        allowed_mentions = AllowedMentions.none()
    embed = Embed2(color=Color2.red(), title=f'Error: {title}', description=msg).set_timestamp(None)
    await ctx.reply(embed=embed, delete_after=autodelete, allowed_mentions=allowed_mentions)


async def explain_exception(ctx: Context, exc: Exception):
    for _, _, exc_t, handler in reversed(exception_handlers):
        if not isinstance(exc, exc_t):
            continue
        explanation = await handler(ctx, exc)
        if explanation is False:
            break
        if explanation is None:
            continue
        msg, autodelete = explanation
        title = exception_names.get(exc_t, 'Error')
        return await reply_command_failure(ctx, title, msg, autodelete)


def prepend_argument_hint(sep='\n\n'):
    def wrapper(f: _ExceptionHandler):
        @wraps(f)
        async def handler(ctx: Context, exc: errors.UserInputError):
            from .manual import get_manual
            should_log = await f(ctx, exc)
            if not should_log:
                return
            if not get_manual:
                return
            msg, autodelete = should_log
            man = get_manual(ctx)
            doc = man.lookup(ctx.command.qualified_name)
            arg_info, arg = doc.format_argument_highlight(ctx.args, ctx.kwargs, 'red')
            arg_info = f'> {ctx.prefix}{full_invoked_with(ctx)} {arg_info}'
            if arg.help:
                arg_info = f'{arg_info}\n{strong(arg.key)}: {arg.help}'
            msg = f'{arg_info}{sep}{msg}'
            return msg, autodelete
        return handler
    return wrapper


def append_matching_quotes_hint():
    example = code('"There\\"s a quote in this sentence"')
    backslash = code('\\')

    def wrapper(f: _ExceptionHandler):
        @wraps(f)
        async def handler(ctx: Context, exc: errors.UserInputError):
            should_log = await f(ctx, exc)
            if not should_log:
                return
            msg, autodelete = should_log
            msg = (f'{msg}\n\nIf you need to provide an argument with a double quote in it, '
                   f'put a backslash {backslash} in front of the quote: {example}')
            return msg, autodelete
        return handler
    return wrapper


def append_quotation_hint():
    example_correct = code('poll "Bring back Blurple"')
    example_incorrect = f'{code("poll Bring back Blurple")} (will be recognized as 3 arguments)'

    def wrapper(f: _ExceptionHandler):
        @wraps(f)
        async def handler(ctx: Context, exc: errors.UserInputError):
            should_log = await f(ctx, exc)
            if not should_log:
                return
            msg, autodelete = should_log
            msg = (f'{msg}\n\nMake sure you spelled arguments correctly.'
                   '\n\nIf some of the arguments have spaces in them '
                   '(e.g. role names or nicknames), you will need to quote them in double quotes:\n'
                   f'✅ {example_correct}\n🔴 {example_incorrect}')
            return msg, autodelete
        return handler
    return wrapper


def describe_concurrency(number: int, bucket: BucketType):
    bucket_type = BUCKET_DESCRIPTIONS[bucket]
    info = (f'concurrency: maximum {number} {pluralize(number, "call")} '
            f'running at the same time {bucket_type}')
    return info


@explains(errors.CommandOnCooldown, 'Command on cooldown', 0)
async def on_cooldown(ctx, exc: errors.CommandOnCooldown):
    cooldown = exc.cooldown.per
    try:
        from pendulum import duration
    except ModuleNotFoundError:
        cooldown_words = f'{cooldown:.0f}s'
        retry_words = f'{exc.retry_after:.0f}s'
    else:
        cooldown_words = duration(seconds=cooldown).in_words()
        retry_words = duration(seconds=exc.retry_after).in_words()
    return (
        f'This command has a cooldown of {cooldown_words}\n'
        f'Try again in {retry_words}'
    ), 10


@explains(errors.MissingRole, 'Missing roles', 0)
async def on_missing_role(ctx, exc):
    explanation = f'You are missing the {tag_literal("role", exc.missing_role)} role.'
    return explanation, 20


@explains(errors.MissingAnyRole, 'Missing roles', 0)
async def on_missing_any_role(ctx, exc):
    roles = pl_cat_predicative('role', [tag_literal('role', r) for r in exc.missing_roles], conj='or')
    explanation = f'You are missing the {roles}.'
    return explanation, 20


@explains(errors.CheckFailure, 'Not allowed', -10)
async def on_generic_check_failure(ctx, exc):
    return 'You are not allowed to use this command.', 20


@explains(errors.CheckAnyFailure, 'Not allowed', -10)
async def on_check_any_failure(ctx, exc: errors.CheckAnyFailure):
    reasons = '\n'.join([f'- {e}' for e in exc.errors])
    return f'You are not allowed to use this command:\n{reasons}', 20


@explains(errors.NoPrivateMessage, 'Server-only', -10)
@explains(errors.PrivateMessageOnly, 'Server-only', -10)
async def on_wrong_context(ctx, exc):
    return False


@explains(errors.ExpectedClosingQuoteError, 'No closing quote found')
async def on_unexpected_eof(ctx, exc: errors.ExpectedClosingQuoteError):
    return (f'Expected another {code(exc.close_quote)} at the end. '
            'Make sure your opening and closing quotes match.'), 60


@explains(errors.UnexpectedQuoteError, 'Unexpected quote')
@append_matching_quotes_hint()
async def on_unexpected_quote(ctx, exc: errors.UnexpectedQuoteError):
    return f'\n> {indicate_eol(ctx.view)} ⚠️ Did not expect a {code(exc.quote)} here', 60


@explains(errors.InvalidEndOfQuotedStringError, 'Missing spaces after quotes')
@append_matching_quotes_hint()
async def on_unexpected_char_after_quote(ctx, exc: errors.InvalidEndOfQuotedStringError):
    return (f'\n> {indicate_eol(ctx.view)} ⚠️ There should be a space before this '
            f'character {code(exc.char)} after the quote.'), 60


@explains(errors.MissingRequiredArgument, 'Not enough arguments')
@prepend_argument_hint(sep='\n⚠️ ')
async def on_missing_args(ctx, exc):
    return 'This argument is missing.', 60


@explains(errors.TooManyArguments, 'Too many arguments')
@append_quotation_hint()
async def on_too_many_args(ctx, exc: errors.TooManyArguments):
    return f'\n> {indicate_extra_text(ctx.view)} ⚠️ {strong("Unrecognized argument found.")}', 60


@explains((
    errors.MessageNotFound,
    errors.MemberNotFound,
    errors.UserNotFound,
    errors.ChannelNotFound,
    errors.RoleNotFound,
    errors.EmojiNotFound,
), 'Not found', priority=5)
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_not_found(ctx: Context, exc) -> tuple[str, int]:
    return escape_markdown(str(exc)), 30


@explains(errors.PartialEmojiConversionFailure, 'Emote not found', priority=5)
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_emote_not_found(ctx: Context, exc: errors.PartialEmojiConversionFailure) -> tuple[str, int]:
    return f'{escape_markdown(exc.argument)} is not an emote or is not in a valid Discord emote format.', 30


@explains(errors.BadInviteArgument, 'Invalid invite')
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_bad_invite(ctx: Context, exc: errors.BadInviteArgument) -> tuple[str, int]:
    return strong(escape_markdown(str(exc))), 30


@explains(errors.BadBoolArgument, 'Incorrect value to a true/false argument')
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_bad_boolean(ctx: Context, exc: errors.BadBoolArgument) -> tuple[str, int]:
    return ((strong(escape_markdown(exc.argument)) + ' is not an acceptable answer to a true/false question in English.\n\n')
            + ('The following are considered to be true: '
               'yes, y, true, t, 1, enable, on\n'
               'The following are considered to be false: '
               'no, n, false, f, 0, disable, off')), 60


@explains(errors.ChannelNotReadable, 'No access to channel')
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_channel_not_readable(ctx: Context, exc) -> tuple[str, int]:
    return escape_markdown(str(exc)), 30


@explains(errors.BadColourArgument, 'Incorrect color format', priority=5)
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_bad_color(ctx: Context, exc: errors.BadColourArgument) -> tuple[str, int]:
    example = code('"rgb(255, 255, 255)"')
    return (f'{strong(escape_markdown(str(exc)))}\n\nTo provide a color in the RGB format that also contains '
            f'spaces, be sure to quote it in double quotes: {example}'), 30


@explains(errors.BadUnionArgument, 'Did not understand argument', 0)
@prepend_argument_hint(sep='\n⚠️ ')
async def on_bad_union(ctx, exc: errors.BadUnionArgument):
    return 'Could not recognize this argument as any of the above.', 45


@explains(errors.BadArgument, 'Did not understand argument', -1)
@prepend_argument_hint(sep='\n⚠️ ')
async def on_bad_args(ctx, exc):
    return escape_markdown(str(exc)), 30


@explains(errors.NotOwner, 'Not owner', priority=100)
async def on_not_owner(ctx, exc):
    return False


@explains(errors.MaxConcurrencyReached, 'Too many instances of this command running', 0)
async def on_max_concurrent(ctx, exc):
    return f'This command allows {describe_concurrency(exc.number, exc.per)}', 10


@explains(errors.MissingPermissions, 'Missing permissions', 0)
async def on_missing_perms(ctx, exc):
    perms = pl_cat_predicative('permission', [strong(readable_perm_name(p)) for p in exc.missing_perms])
    explanation = f'You are missing the {perms} in this server.'
    return explanation, 20


@explains(errors.CommandNotFound, 'Command not found', -10)
async def on_cmd_not_found(ctx: Context, exc: errors.CommandNotFound):
    return False


@explains(Exception, 'Error', -100)
async def on_exception(ctx, exc):
    return 'Error while processing the command.', 20


@explains(exceptions.ReplyRequired, 'Message reference required', priority=5)
async def explains_required_reply(ctx, exc) -> tuple[str, int]:
    return str(exc), 20


@explains(exceptions.NotAcceptable, 'Item not acceptable', priority=5)
async def explains_not_acceptable(ctx, exc) -> tuple[str, int]:
    return str(exc), 60


@explains(exceptions.SendHelp, priority=50)
async def send_help(ctx, exc: exceptions.SendHelp):
    await ctx.send_help(ctx.command.qualified_name, exc.category)
    if isinstance(exc.__cause__, Exception):
        await explain_exception(ctx, exc.__cause__)
    return False
