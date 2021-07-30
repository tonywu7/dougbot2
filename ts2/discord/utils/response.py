# response.py
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

from collections.abc import Callable, Coroutine
from typing import Any, Optional

import attr
from discord import AllowedMentions, File, Forbidden, Message, MessageReference
from discord.ext.commands import Context

from .duckcord.embeds import Embed2
from .events import (DeleteResponder, Responder, run_responders,
                     start_responders)
from .markdown import tag


@attr.s
class ResponseInit:
    context: Context = attr.ib()

    content: Optional[str] = attr.ib(default=None)
    embed: Optional[Embed2] = attr.ib(default=None)
    files: list[File] = attr.ib(default=attr.Factory(list))
    nonce: Optional[int] = attr.ib(default=None)

    delete_after: Optional[float] = attr.ib(default=None)
    allowed_mentions: Optional[AllowedMentions] = attr.ib(default=None)
    reference: Optional[Message | MessageReference] = attr.ib(default=None)
    mention_author: bool = attr.ib(default=False)

    callbacks: list[Callable[[Message], Coroutine]] = attr.ib(default=attr.Factory(list))
    responders: list[Callable[[Message], Responder]] = attr.ib(default=attr.Factory(list))
    direct_message: bool = attr.ib(default=False)

    def timed(self, ttl: float):
        return attr.evolve(self, delete_after=ttl)

    def mentions(self, mentions: AllowedMentions | None):
        if mentions is None:
            mentions = AllowedMentions.none()
        return attr.evolve(self, allowed_mentions=mentions)

    def reply(self, notify: bool = False):
        return attr.evolve(self, reference=self.context.message, mention_author=notify)

    def pingback(self):
        content = self.content or ''
        content = f'{tag(self.context.author)} {content}'
        return attr.evolve(self, content=content)

    def responder(self, responder_init: Callable[[Message], Responder]):
        init = attr.evolve(self)
        init.responders = [*self.responders, responder_init]
        return init

    def callback(self, cb: Callable[[Message], Coroutine[None, None, Any]]):
        init = attr.evolve(self)
        init.callbacks = [*self.callbacks, cb]
        return init

    def deleter(self):
        return self.responder(lambda msg: DeleteResponder(self.context, msg))

    def suppress(self):
        async def callback(msg: Message):
            return await msg.edit(suppress=True)
        return self.callback(callback)

    def dm(self):
        return attr.evolve(self, direct_message=True)

    async def send(self, *args, **kwargs) -> Optional[Message]:
        if self.direct_message:
            try:
                return await self.context.author.send(*args, **kwargs)
            except Forbidden:
                return
        return await self.context.send(*args, **kwargs)

    async def run(self, message: Optional[Message] = None, thread: bool = True):
        if not message:
            if self.is_empty:
                return
            args = attr.asdict(self, recurse=False)
            del args['context']
            del args['callbacks']
            del args['responders']
            del args['direct_message']
            if len(args['files']) == 1:
                args['file'] = args['files'].pop()
            message = await self.send(**args)
        if not message:
            return
        for cb in self.callbacks:
            await cb(message)
        if self.responders:
            tasks = [r(message) for r in self.responders]
            if thread:
                start_responders(*tasks)
            else:
                await run_responders(*tasks)
        return message

    @property
    def is_empty(self):
        return not self.content and not self.embed and not self.files
