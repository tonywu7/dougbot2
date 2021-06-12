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

from __future__ import annotations

import asyncio
import logging
import threading
from importlib import import_module
from pathlib import Path
from typing import Dict, Type

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import caches

from discord import Client, Message, Permissions
from discord.ext.commands import Bot
from telescope2.utils.importutil import iter_module_tree

from . import ipc
from .models import Server


class BotRunner(threading.Thread):
    def __init__(self, client_cls: Type[Client], client_opts: Dict, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._client_cls = client_cls
        self._client_options = client_opts

    def run_client(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        client = self._client_cls(loop=loop, **self._client_options)
        global instance
        instance = client
        loop.create_task(client.start(settings.DISCORD_BOT_TOKEN))
        loop.run_forever()

    def run(self) -> None:
        return self.run_client()


class Telescope(Bot):

    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(805825782)

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        super().__init__(loop=loop, command_prefix=self.which_prefix, **options)
        self.log = logging.getLogger('telescope')
        self._register_events()
        self._register_commands()
        self._init_ipc()
        self._refresh()

    def _init_ipc(self):
        thread = ipc.CachePollingThread('discord')
        thread.add_event_listener('telescope2.discord.bot.refresh', self._refresh)
        thread.start()

    def _register_events(self):
        @self.event
        async def on_ready():
            self.log.info('Bot ready')
            self.log.info(f'User {self.user}')

    def _register_commands(self):
        for parts in iter_module_tree(str(Path(__file__).with_name('commands')), 1):
            module_path = f'.commands.{".".join(parts)}'
            command_module = import_module(module_path, __package__)
            try:
                command_module.register_all(self)
            except AttributeError:
                pass
            else:
                self.log.info(f'Loaded commands from {module_path}')

    @classmethod
    async def _get_prefix(cls, *, bot_id: int, guild_id: int):
        @sync_to_async
        def get():
            return Server.objects.get(pk=guild_id).prefix
        try:
            return [await get(), f'<@{bot_id}> ']
        except Server.DoesNotExist:
            return [cls.DEFAULT_PREFIX, f'<@{bot_id}> ']

    @classmethod
    async def which_prefix(cls, bot: Bot, msg: Message):
        bot_id = bot.user.id
        if msg.guild is None:
            return [cls.DEFAULT_PREFIX, f'<@{bot_id}> ']
        return await cls._get_prefix(bot_id=bot_id, guild_id=msg.guild.id)

    @classmethod
    def schedule_refresh(cls):
        caches['discord'].set('telescope2.discord.bot.refresh', True)

    async def _refresh(self, *args, **kwargs):
        self.log.info('Refreshing extensions')
