# decorators.py
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

from collections.abc import Callable
from typing import Any, Literal, Optional, Union

import discord
from discord import MessageReference
from discord.ext import commands
from discord.ext.commands import Cog, Command, Context
from more_itertools import always_iterable

from ...utils.english import (BUCKET_DESCRIPTIONS, QuantifiedNP,
                              describe_concurrency, pluralize)
from ...utils.functional import memoize
from .environment import CheckDecorator, CheckWrapper, Documentation
from .exceptions import ReplyRequired


def example(invocation: Union[str, tuple[str, ...]], explanation: str):
    """Add an example of how to use this command to its documentation.

    :param invocation: How people should invoke this specific example.
    :type invocation: str | tuple[str, ...]
    :param explanation: What this example does when invoked.
    :type explanation: str
    """
    def wrapper(doc: Documentation, f: Command):
        key = tuple(f'{doc.call_sign} {inv}' for inv in always_iterable(invocation))
        doc.examples[key] = explanation

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def description(desc: str):
    """Set the description of this command."""
    def wrapper(doc: Documentation, f: Command):
        doc.description = desc

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def discussion(title: str, body: str):
    """Append an additional section to this command's documentation."""
    def wrapper(doc: Documentation, f: Command):
        doc.discussions[title] = body

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def argument(arg: str, help: Union[str, Literal[False]] = '', *, node: str = '',
             signature: str = '', term: Optional[Union[str, QuantifiedNP]] = None):
    """Describe an argument of this command.

    :param arg: The name of the argument as specified on the signature.
    :type arg: str
    :param help: Explanation of the argument, defaults to ''
    :type help: str, optional
    :param node: How the argument should be printed as part of the invocation signature,\
        defaults to '' (autogenerate)
    :type node: str, optional
    :param signature: How the argument should be printed as part of the command signature,\
        defaults to '' (autogenerate)
    :type signature: str, optional
    :param term: How the type of the argument should be expressed in plain English,\
        defaults to None
    :type term: Optional[Union[str, QuantifiedNP]], optional
    """
    def wrapper(doc: Documentation, f: Command):
        argument = doc.arguments[arg]
        if help is False:
            argument.hidden = True
        else:
            argument.help = help
        argument.node = node
        argument.signature = signature
        if isinstance(term, QuantifiedNP):
            argument.accepts = term
        elif isinstance(term, str):
            argument.accepts = QuantifiedNP(term)

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def invocation(signature: tuple[str, ...], desc: Union[str, None, Literal[False]]):
    """Describe a specific invocation style of this command.

    For commands that accept optional arguments and varargs and vary their
    behaviors based on what parameters are provided, each possible way to call
    the command should be documented separately using this decorator.

    :param signature: The set of arguments; a single argument must be\
        wrapped in a tuple.
    :type signature: tuple[str, ...]
    :param desc: What the command will do when this set of arguments are\
        passed.
    :type desc: Union[str, bool]
    :raises KeyError: If the passed signature is not a possible invocation
    """
    signature: frozenset[str] = frozenset(signature)

    def wrapper(doc: Documentation, f: Command):
        doc.ensure_signatures()
        if desc or desc is None:
            doc.invocations[signature].description = desc
            doc.invocations.move_to_end(signature, last=True)
            doc.invalid_syntaxes.discard(signature)
        else:
            if signature not in doc.invocations:
                raise KeyError(signature)
            doc.invalid_syntaxes.add(signature)

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def use_syntax_whitelist(f):
    """Mark all possible invocations of this command as invalid.

    By default, all invocations are assumed to be valid. Use this for when
    there are a large amount of invocation styles but only some of them can
    be used.
    """
    def wrapper(doc: Documentation, f: Command):
        doc.ensure_signatures()
        doc.invalid_syntaxes |= doc.invocations.keys()
    return memoize(f, '__command_doc__', wrapper)


def restriction(deco_func: Union[CheckDecorator, None], description: Optional[str] = None, /, **kwargs) -> CheckWrapper:
    """Document a check for the command.

    If a function is passed, the function will be called with the supplied
    keyword arguments, the result will be called with the command callback.

    If supported, the function itself will be translated to a description.
    Otherwise the function's docstring will be used.

    :param deco_func: A decorator function.
    :type deco_func: Union[CheckDecorator, None]
    :param description: Description of this check, defaults to None
    :type description: Optional[str], optional
    """
    def wrapper(doc: Documentation, f: Command):
        doc.add_restriction(deco_func, description, **kwargs)

    def deco(f):
        if callable(deco_func):
            deco_func(**kwargs)(f)
        return memoize(f, '__command_doc__', wrapper)
    return deco


def hidden(f):
    """Mark this command as hidden in the command table of contents."""
    def wrapper(doc: Documentation, f: Command):
        doc.hidden = True
    return memoize(f, '__command_doc__', wrapper)


def cooldown(maxcalls: int, duration: float, bucket: Union[commands.BucketType, Callable[[discord.Message], Any]]):
    """Document a cooldown for this command and apply the cooldown."""

    def wrapper(doc: Documentation, f: Command):
        bucket_type = BUCKET_DESCRIPTIONS.get(bucket)
        cooldown = (f'Rate limited: {maxcalls} {pluralize(maxcalls, "command call")} '
                    f'every {duration} {pluralize(duration, "second")}')
        if bucket_type is None:
            info = f'{cooldown}; dynamic.'
        else:
            info = f'{cooldown} {bucket_type}'
        doc.restrictions.append(info)

    def deco(f):
        commands.cooldown(maxcalls, duration, bucket)(f)
        return memoize(f, '__command_doc__', wrapper)
    return deco


def concurrent(number: int, bucket: commands.BucketType, *, wait=False):
    """Document a max concurrency rule for this command and apply the rule."""

    def wrapper(doc: Documentation, f: Command):
        doc.restrictions.append(describe_concurrency(number, bucket).capitalize())

    def deco(f):
        commands.max_concurrency(number, bucket, wait=wait)(f)
        return memoize(f, '__command_doc__', wrapper)
    return deco


def accepts_reply(desc: str = 'Reply to a message', required=False):
    """Mark this command as accepting a reply.

    This will add a `before_invoke` callback to the command to retrieve
    the reply and place it in a keyword argument named `reply`.
    """
    async def inject_reply(self_or_ctx: Union[Cog, Context], *args):
        if not isinstance(self_or_ctx, Context):
            ctx = args[0]
        else:
            ctx = self_or_ctx
        reply: MessageReference = ctx.message.reference
        if reply is None and required:
            raise ReplyRequired()
        ctx.kwargs['reply'] = reply

    def wrapper(doc: Documentation, f: Command):
        f.before_invoke(inject_reply)
        arg = doc.arguments['reply']
        arg.description = desc
        arg.signature = '(with reply)'
        arg.node = '┌ (while replying to a message)\n'
        arg.order = -2

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco
