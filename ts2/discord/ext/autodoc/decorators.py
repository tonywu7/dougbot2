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

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal, Optional

import discord
from discord import MessageReference
from discord.ext import commands
from discord.ext.commands import Cog, Command, Context
from more_itertools import always_iterable

from ts2.utils.functional import memoize

from .documentation import (CheckDecorator, CheckWrapper, Documentation,
                            add_type_converter, add_type_description)
from .exceptions import ReplyRequired
from .explanation import BUCKET_DESCRIPTIONS, describe_concurrency
from .lang import QuantifiedNP, pluralize


def example(invocation: str | tuple[str, ...], explanation: str):
    def wrapper(doc: Documentation, f: Command):
        key = tuple(f'{doc.call_sign} {inv}' for inv in always_iterable(invocation))
        doc.examples[key] = explanation

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def description(desc: str):
    def wrapper(doc: Documentation, f: Command):
        doc.description = desc

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def discussion(title: str, body: str):
    def wrapper(doc: Documentation, f: Command):
        doc.discussions[title] = body

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


def argument(arg: str, help: str = '', *, node: str = '',
             signature: str = '', term: Optional[str | QuantifiedNP] = None):
    def wrapper(doc: Documentation, f: Command):
        argument = doc.arguments[arg]
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


def invocation(signature: tuple[str, ...], desc: str | Literal[False]):
    signature: frozenset[str] = frozenset(signature)

    def wrapper(doc: Documentation, f: Command):
        doc.ensure_signatures()
        if desc:
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
    def wrapper(doc: Documentation, f: Command):
        doc.ensure_signatures()
        doc.invalid_syntaxes |= doc.invocations.keys()
    return memoize(f, '__command_doc__', wrapper)


def restriction(deco_func_or_desc: CheckDecorator | str, *args, **kwargs) -> CheckWrapper:
    def wrapper(doc: Documentation, f: Command):
        if callable(deco_func_or_desc):
            doc.add_restriction(deco_func_or_desc, *args, **kwargs)
        else:
            doc.restrictions.append(deco_func_or_desc)

    def deco(f):
        if callable(deco_func_or_desc):
            deco_func_or_desc(*args, **kwargs)(f)
        return memoize(f, '__command_doc__', wrapper)
    return deco


def hidden(f):
    def wrapper(doc: Documentation, f: Command):
        doc.hidden = True
    return memoize(f, '__command_doc__', wrapper)


def cooldown(maxcalls: int, duration: float, bucket: commands.BucketType | Callable[[discord.Message], Any]):
    def wrapper(doc: Documentation, f: Command):
        bucket_type = BUCKET_DESCRIPTIONS.get(bucket)
        cooldown = (f'Rate limited: {maxcalls} {pluralize(maxcalls, "call")} '
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
    def wrapper(doc: Documentation, f: Command):
        doc.restrictions.append(describe_concurrency(number, bucket).capitalize())

    def deco(f):
        commands.max_concurrency(number, bucket, wait=wait)(f)
        return memoize(f, '__command_doc__', wrapper)
    return deco


def accepts_reply(desc: str = 'Reply to a message', required=False):
    async def inject_reply(self_or_ctx: Cog | Context, *args):
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


def accepts(*args, **kwargs):
    def wrapper(obj: Any):
        add_type_description(obj, QuantifiedNP(*args, **kwargs))
        return obj
    return wrapper


def convert_with(c: Callable):
    def wrapper(obj: Any):
        add_type_converter(obj, c)
        return obj
    return wrapper
