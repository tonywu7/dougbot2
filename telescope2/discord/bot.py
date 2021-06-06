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
from urllib.parse import urlencode, urlunsplit

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest
from django.urls import reverse
from django.utils.functional import classproperty

from discord import Client, Message, Permissions
from discord.ext.commands import Bot
from telescope2.utils.importutil import iter_module_tree

instance: Telescope = None
thread: threading.Thread = None


class BotThread(threading.Thread):
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
        loop.create_task(client.start(settings.DISCORD_SECRET))
        loop.run_forever()

    def run(self) -> None:
        return self.run_client()


class Telescope(Bot):
    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(805825782)

    @classmethod
    def get_thread(cls) -> threading.Thread:
        return thread

    @classmethod
    def get_instance(cls) -> Telescope:
        return instance

    @classproperty
    def is_alive(cls) -> bool:
        return thread and thread.is_alive()

    @classmethod
    def run(cls):
        options = {
            'command_prefix': Telescope.which_prefix,
        }
        global thread
        thread = BotThread(Telescope, options, daemon=True)
        thread.start()

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        super().__init__(loop=loop, **options)
        self.log = logging.getLogger('telescope')
        self.register_events()
        self.register_commands()

    def register_events(self):
        @self.event
        async def on_ready():
            self.log.info('Bot ready')
            self.log.info(f'User {self.user}')

    def register_commands(self):
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
    def build_oauth2_url(cls, req: HttpRequest) -> str:
        protocol = 'http'
        domain = 'discord.com'
        path = '/oauth2/authorize'

        bot = cls.get_instance()
        site = get_current_site(req)
        redirect = urlunsplit((req.scheme, site.domain, reverse('bot.authorized'), '', ''))
        params = {
            'client_id': bot.user.id,
            'permissions': bot.DEFAULT_PERMS.value,
            'scope': 'bot',
            'response_type': 'code',
            'redirect_uri': redirect,
        }
        query = urlencode(params)
        return urlunsplit((protocol, domain, path, query, ''))

    @classmethod
    @sync_to_async
    def which_prefix(cls, bot: Bot, msg: Message):
        from .models import GuildPreference

        user_id = bot.user.id
        prefixes = [f'<@!{user_id}> ', f'<@{user_id}> ']
        if msg.guild is None:
            prefixes.append(cls.DEFAULT_PREFIX)
            return prefixes

        try:
            prefs = GuildPreference.prefs_by_guild(msg.guild)
        except GuildPreference.DoesNotExist:
            prefixes.append(cls.DEFAULT_PREFIX)
        else:
            prefixes.append(prefs.prefix)
        return prefixes
