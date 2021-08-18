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
import random
from collections import defaultdict
from collections.abc import Callable, Coroutine
from functools import wraps
from typing import Literal, Optional, Union

from discord import AllowedMentions
from discord.ext.commands import Context, errors

from ...utils.duckcord.color import Color2
from ...utils.duckcord.embeds import Embed2
from ...utils.markdown import code, strong

_ExceptionType = Union[type[Exception], tuple[type[Exception], ...]]
_ExceptionHandler = Callable[[Context, Exception], Coroutine[None, None, Union[tuple[str, float], Literal[False], None]]]

exception_handlers: list[tuple[int, str, _ExceptionType, _ExceptionHandler]] = []
exception_names: dict[_ExceptionType, set[str]] = defaultdict(set)


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
            exception_names[exc].add(name)
        return f
    return wrapper


async def reply_command_failure(ctx: Context, title: str, msg: str,
                                autodelete: float = 60, ping=False):
    if ping:
        allowed_mentions = AllowedMentions(everyone=False, roles=False, users=False, replied_user=True)
    else:
        allowed_mentions = AllowedMentions.none()
    embed = Embed2(color=Color2.red(), title=title, description=msg).set_timestamp(None)
    await ctx.send(embed=embed, delete_after=autodelete, allowed_mentions=allowed_mentions)


async def explain_exception(ctx: Context, exc: Exception):
    if isinstance(exc, errors.CommandInvokeError):
        exc = exc.original or exc.__cause__
    for _, _, exc_t, handler in reversed(exception_handlers):
        if not isinstance(exc, exc_t):
            continue
        explanation = await handler(ctx, exc)
        if explanation is False:
            break
        if explanation is None:
            continue
        msg, autodelete = explanation
        titles = exception_names.get(exc_t)
        if not titles:
            title = 'Error'
        elif len(titles) == 1:
            title = [*titles][0]
        else:
            title = random.choice([*titles])
        return await reply_command_failure(ctx, title, msg, autodelete)


def prepend_argument_hint(sep='\n\n', include_types=False):
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
            doc = man.lookup(ctx.command.qualified_name, hidden=True)
            arg_info, arg = doc.format_argument_highlight(ctx.args, ctx.kwargs, 'red')
            arg_info = f'> {ctx.prefix}{full_invoked_with(ctx)} {arg_info}'
            if include_types:
                arg_info = f'{arg_info}\n{strong(arg.key)}: {arg.describe()}'
            elif arg.help:
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


def add_error_names(exc: _ExceptionType, *names: str):
    if not isinstance(exc, tuple):
        exc = (exc,)
    for e in exc:
        for exc_t, exc_titles in exception_names.items():
            if e in exc_t:
                exc_titles.update(names)
