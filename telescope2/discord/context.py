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

import logging
import traceback
from functools import partialmethod, wraps
from typing import Dict, List, Optional, Tuple, TypedDict

from asgiref.sync import sync_to_async
from discord import (
    AllowedMentions, Embed, Guild, Member, Message, Role, TextChannel,
)
from discord.ext.commands import Bot, Command, Context
from discord.utils import escape_markdown
from django.db import transaction

from telescope2.utils.discord import tag, unmarked

from .models import Server


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


class _LoggingConf(TypedDict):
    name: str
    channel: int
    role: Optional[int]


# 'Cause of ...
class Circumstances(Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        self.log = ContextualLogger('discord.logging', self)
        self._server: Server

        self.message: Message
        self.command: Command
        self.bot: Bot
        self.invoked_with: str
        self.invoked_parents: List[str]
        self.invoked_subcommand: Command | None

        self.author: Member
        self.guild: Guild

    @property
    @_guard('Context is missing server instance')
    def server(self) -> Server:
        return self._server

    @property
    @_guard('Context is missing server instance')
    def log_config(self) -> Dict:
        return self._logging_conf

    async def init(self):
        await self._get_server()

    @sync_to_async
    def _get_server(self):
        try:
            self._server = (
                Server.objects.prefetch_related('channels', 'roles')
                .get(pk=self.message.guild.id)
            )
            self._logging_conf = self._server.logging
        except AttributeError:
            return
        except Server.DoesNotExist:
            raise

    @sync_to_async
    def set_prefix(self, prefix: str):
        Server.validate_prefix(prefix)
        with transaction.atomic():
            self.server.prefix = prefix
            self.server.save()


class ContextualLogger:
    def __init__(self, prefix: str, ctx: Circumstances):
        self.prefix = prefix
        self.ctx = ctx

    async def log(self, msg_class: str, level: int, msg: str, *args,
                  exc_info: Optional[BaseException] = None,
                  embed: Optional[Embed] = None, **kwargs):
        logger = logging.getLogger(f'{self.prefix}.{msg_class}')
        logger.log(level, unmarked(msg), *args, exc_info=exc_info, **kwargs)
        await self.deliver(msg_class, msg, embed, exc_info)

    def get_dest_info(self, msg_class: str) -> Tuple[TextChannel, str, Role | None]:
        config: _LoggingConf | None = self.ctx.log_config.get(msg_class)
        if not config:
            raise LookupError
        channel = config.get('channel')
        if not channel:
            raise LookupError
        channel: TextChannel = self.ctx.guild.get_channel(channel)
        if not isinstance(channel, TextChannel):
            raise LookupError
        role = config.get('role', None)
        if role:
            role: Role = self.ctx.guild.get_role(role)
        name = config.get('name', 'Logging')
        return channel, name, role

    async def deliver(self, msg_class: str, msg: str,
                      embed: Optional[Embed] = None,
                      exc_info: Optional[BaseException] = None):
        try:
            channel, name, role = self.get_dest_info(msg_class)
        except LookupError:
            return
        msg = f'**{escape_markdown(name)}**\n{msg}'
        if role:
            msg = f'{tag(role)}\n{msg}'
            mentions = AllowedMentions(roles=[role])
        else:
            mentions = AllowedMentions.none()

        await channel.send(content=msg, allowed_mentions=mentions, embed=embed)
        await self.report_exception(channel, exc_info)

    async def report_exception(self, channel: TextChannel, exc_info: BaseException):
        if not isinstance(exc_info, BaseException):
            return
        tb = traceback.format_exception(type(exc_info), exc_info)
        tb_body = ''.join(tb)
        tb_body = f'```python\n{tb_body}\n```'
        embed = Embed(title=type(exc_info).__name__, description=tb_body)
        await channel.send(embed=embed)

    debug = partialmethod(log, level=logging.DEBUG)
    info = partialmethod(log, level=logging.INFO)
    warning = partialmethod(log, level=logging.WARNING)
    error = partialmethod(log, level=logging.ERROR)
    critical = partialmethod(log, level=logging.CRITICAL)
