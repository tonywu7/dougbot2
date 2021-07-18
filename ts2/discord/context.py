# context.py
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
from contextlib import asynccontextmanager
from functools import wraps

from asgiref.sync import sync_to_async
from discord import (AllowedMentions, Embed, Guild, Member, Message,
                     TextChannel, User)
from discord.abc import Messageable
from discord.errors import Forbidden
from discord.ext.commands import Command, Context
from discord.ext.commands.errors import CommandInvokeError
from django.db import transaction

from .models import Server
from .utils.markdown import tag


def _guard(err: str):
    def wrapper(f):
        @wraps(f)
        def wrapped(self):
            try:
                return f(self)
            except AttributeError:
                raise ValueError(err)
        return wrapped
    return wrapper


# 'Cause of ...
class Circumstances(Context):

    send: Callable[..., Coroutine[None, None, Message]]
    reply: Callable[..., Coroutine[None, None, Message]]

    NOTIFY_REPLY = AllowedMentions(replied_user=True)

    def __init__(self, **attrs):
        super().__init__(**attrs)
        from .bot import Robot
        from .ext.logging import ContextualLogger

        self.log = ContextualLogger('discord.logging', self)
        self._server: Server

        self.me: Member | User
        self.message: Message | Messageable
        self.command: Command
        self.invoked_with: str
        self.invoked_parents: list[str]
        self.invoked_subcommand: Command | None

        self.author: Member | Messageable
        self.guild: Guild
        self.channel: TextChannel

        self.bot: Robot
        self.prefix: str

        self.session = self.bot.request

    @property
    @_guard('Context is missing server instance')
    def server(self):
        return self._server

    @property
    @_guard('Context is missing server instance')
    def log_config(self) -> dict:
        return self._logging_conf

    async def init(self):
        await self._get_server()

    @sync_to_async
    def _get_server(self):
        from .models import Server
        try:
            self._server = (
                Server.objects
                .prefetch_related('channels', 'roles')
                .get(pk=self.message.guild.id)
            )
            self._logging_conf = self._server.logging
        except AttributeError:
            return
        except Server.DoesNotExist:
            raise

    @sync_to_async
    def set_prefix(self, prefix: str):
        from .models import validate_prefix
        validate_prefix(prefix)
        with transaction.atomic():
            self.server.prefix = prefix
            self.server.save()

    async def pingback(self, content=None, *args, **kwargs):
        content = content or ''
        content = f'{tag(self.author)} {content}'
        return await self.send(content=content, *args, **kwargs)

    async def reply_with_delete(self, *args, **kwargs):
        msg = await self.reply(*args, **kwargs)
        try:
            await msg.add_reaction('🗑')
        except Forbidden:
            pass
        return msg

    async def reply_with_text_fallback(self, embed: Embed, text: str, **kwargs) -> tuple[Message, bool]:
        try:
            return await self.reply_with_delete(embed=embed, **kwargs), True
        except Forbidden:
            return await self.reply_with_delete(content=text, **kwargs), False

    @property
    def full_invoked_with(self) -> str:
        if self.invoked_parents:
            return f'{self.prefix}{" ".join(self.invoked_parents)} {self.invoked_with}'
        return f'{self.prefix}{self.invoked_with}'

    @property
    def raw_input(self) -> str:
        return self.view.buffer[len(self.full_invoked_with):].strip()

    async def send_help(self, query: str = None, category='normal'):
        query = query or self.command.qualified_name
        return await self.bot.send_help(self, category, query=query)

    async def call(self, cmd: Command, *args, **kwargs):
        async with self.acquire_concurrency(cmd):
            self.trigger_cooldowns(cmd)
            return await self.invoke(cmd, *args, **kwargs)

    @asynccontextmanager
    async def acquire_concurrency(self, cmd: Command):
        try:
            if cmd._max_concurrency is not None:
                await cmd._max_concurrency.acquire(self)
            yield
        finally:
            if cmd._max_concurrency is not None:
                await cmd._max_concurrency.release(self)

    def trigger_cooldowns(self, cmd: Command):
        cmd._prepare_cooldowns(self)


class CommandContextError(CommandInvokeError):
    def __init__(self, exc: Exception):
        self.original = exc
        super().__init__('Command context raised an exception: {0.__class__.__name__}: {0}'.format(exc))
