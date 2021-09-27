# reply.py
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

# FIXME: Remove

from inspect import Parameter, signature
from types import FunctionType
from typing import Union, get_args, get_origin

from discord import Message, MessageReference
from discord.ext.commands import (BadArgument, Command, Context, Converter,
                                  MissingRequiredArgument)

from ...utils.functional import memoize
from ..autodoc.decorators import accepts
from ..types.undefined import strict_undefined


def _get_union_types(annotation) -> set[Union[type, None]]:
    origin = get_origin(annotation)
    if not origin:
        return {annotation}
    if origin is not Union:
        return set()
    constituents = get_args(annotation)
    return set(constituents)


class ReplyRequired(BadArgument):
    def __init__(self):
        msg = 'You need to call this command while replying to a message.'
        super().__init__(message=msg)


class MessageUnresolvable(BadArgument):
    def __init__(self):
        msg = 'Cannot resolve the original message you are replying to.'
        super().__init__(message=msg)


@accepts('message reply', concise='reply')
class Reply(Converter):
    async def convert(self, ctx: Context, arg) -> Message:
        reply: MessageReference = ctx.message.reference
        if not reply:
            raise ReplyRequired()
        if not isinstance(reply.resolved, Message):
            raise MessageUnresolvable()
        return reply.resolved


def accepts_reply(param: str):
    def deco(f: FunctionType):
        sig = signature(f)
        target = sig.parameters.get(param)
        if target is None:
            raise TypeError(f'{f} does not have a parameter "{param}"')

        target_t = target.annotation
        if target_t is None:
            raise TypeError(f'{param} must be annotated.')
        if isinstance(target_t, str):
            target_t = eval(target_t, f.__globals__)

        types = _get_union_types(target_t)
        if types != {Message, type(None)} and types != {Message}:
            raise TypeError((
                f'Parameter {param} must have'
                ' either discord.Message'
                ' or Optional[discord.Message]'
                ' as its type signature.'
            ))

        f.__annotations__[param] = Union[Reply, target_t]

        if target.default is not Parameter.empty:
            return f

        def autodoc_rider(doc, c: Command):
            p = c.params[param]
            exc = MissingRequiredArgument(p)
            p._default = strict_undefined(exc)
        return memoize(f, '__command_doc__', autodoc_rider)
    return deco
