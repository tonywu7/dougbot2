# errors.py
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
from typing import Literal, Optional, Tuple, Union

from discord import AllowedMentions
from discord.ext.commands import errors
from discord.utils import escape_markdown
from pendulum import duration

from telescope2.utils.lang import pl_cat_predicative

from .constraint import ConstraintFailure
from .context import Circumstances
from .converters import (InvalidChoices, InvalidSyntax, RegExpMismatch,
                         ReplyRequired)
from .documentation import (NoSuchCommand, NotAcceptable, SendHelp,
                            describe_concurrency, readable_perm_name)
from .extension import ModuleDisabled
from .utils.markdown import (code, indicate_eol, indicate_extra_text, strong,
                             tag_literal)

_ExceptionType = Union[type[Exception], Tuple[type[Exception]]]
_ExceptionHandler = Callable[[Circumstances, Exception], Coroutine[None, None, Union[Tuple[str, float], Literal[False], None]]]

exception_handlers: list[tuple[int, str, _ExceptionType, _ExceptionHandler]] = []
exception_names: dict[_ExceptionType, str] = {}


def explains(exc: _ExceptionType, name: Optional[str] = None, priority=0):
    if not isinstance(exc, tuple):
        exc = (exc,)

    def wrapper(f: _ExceptionHandler):
        heapq.heappush(exception_handlers, (priority, str(exc), exc, f))
        if name:
            exception_names[exc] = name
        return f
    return wrapper


async def reply_command_failure(ctx: Circumstances, title: str, msg: str,
                                autodelete=60, ping=False):
    message = f'⚠️ {strong(title)}\n{msg}'
    if ping:
        allowed_mentions = AllowedMentions(everyone=False, roles=False, users=False, replied_user=True)
    else:
        allowed_mentions = AllowedMentions.none()
    return await ctx.reply(message, delete_after=autodelete, allowed_mentions=allowed_mentions)


async def explain_exception(ctx: Circumstances, exc: Exception):
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


@explains(errors.CommandOnCooldown, 'Command on cooldown', 0)
async def on_cooldown(ctx, exc):
    return f'Try again in {duration(seconds=exc.retry_after).in_words()}', 10


@explains(errors.MaxConcurrencyReached, 'Too many instances of this command running', 0)
async def on_max_concurrent(ctx, exc):
    return f'This command allows {describe_concurrency(exc.number, exc.per)}', 10


@explains(errors.CommandNotFound, 'Command not found', 0)
async def on_not_found(ctx: Circumstances, exc):
    try:
        ctx.bot.manual.lookup(ctx.invoked_with)
    except NoSuchCommand as no_command:
        return str(no_command), 30


@explains(errors.MissingPermissions, 'Missing permissions', 0)
async def on_missing_perms(ctx, exc):
    perms = pl_cat_predicative('permission', [strong(readable_perm_name(p)) for p in exc.missing_perms])
    explanation = f'You are missing the {perms}.'
    return explanation, 20


@explains(errors.MissingRole, 'Missing roles', 0)
async def on_missing_role(ctx, exc):
    explanation = f'You are missing the {tag_literal("role", exc.missing_role)} role.'
    return explanation, 20


@explains(errors.MissingAnyRole, 'Missing roles', 0)
async def on_missing_any_role(ctx, exc):
    roles = pl_cat_predicative('role', [tag_literal('role', r) for r in exc.missing_roles], conj='or')
    explanation = f'You are missing the {roles}.'
    return explanation, 20


@explains(ConstraintFailure, 'Missing roles', 0)
async def on_constraint_failure(ctx, exc):
    return exc.reply, 30


@explains(SendHelp, priority=50)
async def send_help(ctx: Circumstances, exc: SendHelp):
    await ctx.send_help(ctx.command.qualified_name, exc.category)
    if isinstance(exc.__cause__, Exception):
        await explain_exception(ctx, exc.__cause__)
    return False


def prepend_argument_hint(supply_arg_type: bool = True, sep='\n\n'):
    def wrapper(f: _ExceptionHandler):
        @wraps(f)
        async def handler(ctx: Circumstances, exc: errors.UserInputError):
            should_log = await f(ctx, exc)
            if not should_log:
                return
            msg, autodelete = should_log
            arg_info, arg = ctx.command.doc.format_argument_highlight(ctx.args, ctx.kwargs, 'red')
            arg_info = f'\n> {ctx.full_invoked_with} {arg_info}'
            if supply_arg_type:
                arg_info = f'{arg_info}\n{strong(arg)}: {arg.describe()}'
            msg = f'{arg_info}{sep}{msg}'
            return msg, autodelete
        return handler
    return wrapper


def append_matching_quotes_hint():
    example = code('"There\\"s a quote in this sentence"')
    backslash = code('\\')

    def wrapper(f: _ExceptionHandler):
        @wraps(f)
        async def handler(ctx: Circumstances, exc: errors.UserInputError):
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
        async def handler(ctx: Circumstances, exc: errors.UserInputError):
            should_log = await f(ctx, exc)
            if not should_log:
                return
            msg, autodelete = should_log
            msg = (f"{msg}\n\nThis could happen because the bot couldn't find members/roles by name. Make sure "
                   'you spelled them correctly. If some of the arguments have spaces in them '
                   f"(e.g. role names or nicknames), {strong('you will need to quote them in double quotes')}:\n"
                   f'✅ {example_correct}\n🔴 {example_incorrect}')
            return msg, autodelete
        return handler
    return wrapper


@explains(errors.ExpectedClosingQuoteError, 'No closing quote found')
async def on_unexpected_eof(ctx, exc: errors.ExpectedClosingQuoteError):
    return (f'Expected another {code(exc.close_quote)} at the end. '
            'Make sure your opening and closing quotes match.'), 20


@explains(errors.UnexpectedQuoteError, 'Unexpected quote')
@append_matching_quotes_hint()
async def on_unexpected_quote(ctx, exc: errors.UnexpectedQuoteError):
    return f'\n> {indicate_eol(ctx.view, "red")} ⚠️ Did not expect a {code(exc.quote)} here', 30


@explains(errors.InvalidEndOfQuotedStringError, 'Missing spaces after quotes')
@append_matching_quotes_hint()
async def on_unexpected_char_after_quote(ctx, exc: errors.InvalidEndOfQuotedStringError):
    return (f'\n> {indicate_eol(ctx.view, "red")} ⚠️ There should be a space before this '
            f'character {code(exc.char)} after the quote.'), 30


@explains(errors.MissingRequiredArgument, 'Not enough arguments')
@prepend_argument_hint(True, sep='\n⚠️ ')
async def on_missing_args(ctx, exc):
    return 'This argument is missing.', 20


@explains(errors.TooManyArguments, 'Too many arguments')
@append_quotation_hint()
async def on_too_many_args(ctx, exc: errors.TooManyArguments):
    return f'\n> {indicate_extra_text(ctx.view, "red")} ⚠️ {strong("Extra text found.")}', 60


@explains(RegExpMismatch, 'Pattern mismatch', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_regexp(ctx: Circumstances, exc: RegExpMismatch) -> tuple[str, int]:
    return f'Got {strong(escape_markdown(exc.received))} instead.', 30


@explains(InvalidChoices, 'Invalid choices', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_invalid_choices(ctx: Circumstances, exc: InvalidChoices) -> tuple[str, int]:
    return f'Got {strong(escape_markdown(exc.received))} instead.', 45


@explains(ReplyRequired, 'Message reference required', priority=5)
async def explains_required_reply(ctx: Circumstances, exc) -> tuple[str, int]:
    return str(exc), 20


@explains(NotAcceptable, 'Item not acceptable', priority=5)
async def explains_not_acceptable(ctx: Circumstances, exc) -> tuple[str, int]:
    return str(exc), 30


@explains(InvalidSyntax, 'Usage Error', priority=5)
async def explains_usage_error(ctx: Circumstances, exc) -> tuple[str, int]:
    return str(exc), 30


@explains((
    errors.MessageNotFound,
    errors.MemberNotFound,
    errors.UserNotFound,
    errors.ChannelNotFound,
    errors.RoleNotFound,
    errors.EmojiNotFound,
), 'Not found', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
@append_quotation_hint()
async def explains_not_found(ctx: Circumstances, exc) -> tuple[str, int]:
    return strong(escape_markdown(str(exc))), 30


@explains(errors.PartialEmojiConversionFailure, 'Emote not found', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
@append_quotation_hint()
async def explains_emote_not_found(ctx: Circumstances, exc: errors.PartialEmojiConversionFailure) -> tuple[str, int]:
    return strong(f'{escape_markdown(exc.argument)} is not an emote or is not in a valid Discord emote format.'), 30


@explains(errors.BadInviteArgument, 'Invalid invite')
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_bad_invite(ctx: Circumstances, exc: errors.BadInviteArgument) -> tuple[str, int]:
    return strong(escape_markdown(str(exc))), 30


@explains(errors.BadBoolArgument, 'Incorrect value to a true/false argument')
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_bad_boolean(ctx: Circumstances, exc: errors.BadBoolArgument) -> tuple[str, int]:
    return ((strong(escape_markdown(exc.argument)) + ' is not an acceptable answer to a true/false question in English.\n\n')
            + ('The following are considered to be true: '
               'yes, y, true, t, 1, enable, on\n'
               'The following are considered to be false: '
               'no, n, false, f, 0, disable, off')), 60


@explains(errors.ChannelNotReadable, 'No access to channel')
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_channel_not_readable(ctx: Circumstances, exc) -> tuple[str, int]:
    return strong(escape_markdown(str(exc))), 30


@explains(errors.BadColourArgument, 'Incorrect color format', priority=5)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def explains_bad_color(ctx: Circumstances, exc: errors.BadColourArgument) -> tuple[str, int]:
    example = code('"rgb(255, 255, 255)"')
    return (f'{strong(escape_markdown(str(exc)))}\n\nTo provide a color in the RGB format that also contains '
            f'spaces, be sure to quote it in double quotes: {example}'), 30


@explains(errors.BadUnionArgument, 'Did not understand argument', 0)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def on_bad_union(ctx, exc: errors.BadUnionArgument):
    return strong('Could not recognize this argument as any of the above.'), 45


@explains(errors.BadArgument, 'Did not understand argument', -1)
@prepend_argument_hint(True, sep='\n⚠️ ')
async def on_bad_args(ctx, exc):
    return strong(escape_markdown(str(exc))), 30


@explains(ModuleDisabled, 'Command disabled')
async def on_disabled(ctx, exc: ModuleDisabled):
    return f'This command belongs to the {exc.module} module, which has been disabled.', 20


@explains(Exception, 'Error', -100)
async def on_exception(ctx, exc):
    return 'Error while processing the command.', 20
