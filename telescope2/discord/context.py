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

from functools import wraps
from typing import Dict, List

from asgiref.sync import sync_to_async
from discord import Guild, Member, Message
from discord.ext.commands import Bot, Command, Context
from django.db import transaction

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


# 'Cause of ...
class Circumstances(Context):
    def __init__(self, **attrs):
        super().__init__(**attrs)
        from .logging import ContextualLogger
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
