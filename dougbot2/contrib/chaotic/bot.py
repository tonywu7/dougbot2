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

import random
from collections import deque
from statistics import mean
from typing import Optional

from discord import Message, MessageReference
from discord.ext.commands import command

from dougbot2.discord.cog import Gear
from dougbot2.discord.context import Circumstances
from dougbot2.exts import autodoc as doc
from dougbot2.utils.common import trunc_for_field


def spongebob(
    s: str,
    ratio: float = 0.5,
    *,
    lookback: int = 2,
    bias: float = 0.75,
) -> tuple[str, bool]:
    history: deque[bool] = deque(maxlen=lookback)
    buffer = []
    has_alpha = False
    complement = 1 - bias
    for char in s:
        if not char.isalpha():
            buffer.append(char)
            continue
        has_alpha = True
        change = random.random()
        if history:
            if mean(history) < 0.5:
                change = change * bias + complement
            else:
                change = change * bias
        if change < ratio:
            buffer.append(char.lower())
            history.append(False)
        else:
            buffer.append(char.upper())
            history.append(True)
    res = "".join(buffer)
    return res, has_alpha


class Chaotic(
    Gear,
    name="District: Chaotic",
    order=6,
    description="Useless features.",
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command("spongebob", aliases=("mock",))
    @doc.description("uSELesS FeATure.")
    @doc.argument("content", "The text to transform.")
    @doc.argument("message", "The message whose text content to transform.")
    @doc.accepts_reply("Use the text content of the replied-to message.")
    @doc.use_syntax_whitelist
    @doc.invocation(("content",), None)
    @doc.invocation(("message",), None)
    @doc.invocation(("reply",), None)
    async def mock(
        self,
        ctx: Circumstances,
        message: Optional[Message],
        *,
        content: Optional[str] = "",
        reply: Optional[MessageReference] = None,
        threshold: Optional[float] = 0.5,
    ):
        if not content:
            if not message and reply:
                message = reply.resolved
            if message:
                if message.author == self.bot.user:
                    raise doc.NotAcceptable("no u")
                content = message.content
        if not content:
            as_error = True
            if not message and not reply:
                content = "There's nothing to convert"
            else:
                content = "That message has no text in it"
        else:
            as_error = False
        await ctx.trigger_typing()
        res, has_alpha = spongebob(content, threshold)
        res = trunc_for_field(res, 1920)
        if as_error:
            raise doc.NotAcceptable(res)
        if reply:
            reference = reply
        elif message:
            reference = message.to_reference()
        else:
            reference = ctx.message.to_reference()
        if reference.channel_id != ctx.channel.id:
            reference = None
        await ctx.response(ctx, content=res, reference=reference).deleter().run()
        if not has_alpha:
            err = "There wasn't any letter to change"
            res, *args = spongebob(err, threshold)
            raise doc.NotAcceptable(res)
