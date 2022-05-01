# decorators.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

from typing import Callable, Optional, Union

from discord import Message, MessageReference
from discord.ext.commands import Cog, Command, Context

from dougbot2.exceptions import NotAcceptable
from dougbot2.utils.markdown import code
from dougbot2.utils.memo import memoized_decorator


@memoized_decorator('__reply_utils__')
def accept_reply(arg: str, required: bool = False):
    """Mark this command as accepting a reply.

    This will add a `before_invoke` callback to the command to retrieve
    the reply and place it in a keyword argument named `reply`.
    """
    getter: Optional[Callable[[Context], Optional[Message]]] = None
    setter: Optional[Callable[[Context, Message], None]] = None

    async def inject_reply(self_or_ctx: Union[Cog, Context], *args):
        if not isinstance(self_or_ctx, Context):
            ctx = args[0]
        else:
            ctx = self_or_ctx
        if isinstance(getter(ctx), Message):
            return
        reply: MessageReference = ctx.message.reference
        msg: Optional[Message] = reply and (reply.resolved or reply.cached_message)
        if msg is None and required:
            raise NotAcceptable(
                f'A message (link or ID) is required for argument {code(arg)}.'
                ' Alternatively, use this command while replying to the message'
                f' to be used for argument {code(arg)}.',
            )
        setter(ctx, msg)

    def wrapper(f: Command):
        nonlocal getter
        nonlocal setter

        param = f.params[arg]

        if param.kind is param.KEYWORD_ONLY:

            def getter(ctx: Context):
                return ctx.kwargs.get(arg)

            def setter(ctx: Context, msg: Message):
                ctx.kwargs[arg] = msg

        elif param.kind in (param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD):
            idx = [*f.params].index(arg)

            def getter(ctx: Context):
                return ctx.args[idx]

            def setter(ctx: Context, msg: Message):
                ctx.args[idx] = msg

        else:
            raise TypeError(f'Cannot inject message reply into a parameter that is {param.kind}.')

        f.before_invoke(inject_reply)

    return wrapper
