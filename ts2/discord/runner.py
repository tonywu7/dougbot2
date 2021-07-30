# runner.py
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

import asyncio
import logging
import threading
from collections.abc import Coroutine
from typing import Any, Generic, Optional, TypeVar

from discord import Client
from discord.errors import LoginFailure
from discord.ext.commands import Bot
from django.conf import settings

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)


class BotRunner(threading.Thread, Generic[T]):
    def __init__(self, client_cls: type[T], client_opts: dict,
                 listen=True, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger('discord.runner')

        self._client_cls = client_cls
        self._client_options = client_opts
        self._listen = listen

        self.loop: asyncio.AbstractEventLoop
        self.client: T

        self.bot_init = threading.Condition()
        self.data_requested = threading.Condition()
        self.data_ready = threading.Condition()

        self._request: Coroutine
        self._data: Any

    def get_client(self) -> Optional[T]:
        try:
            return self.client
        except AttributeError:
            return None

    def run_client(self):
        with self.bot_init:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = self._client_cls(loop=loop, **self._client_options)
            self.loop = loop
            self.client = client
            self.bot_init.notify_all()

        if self._listen:
            run = client.start(settings.DISCORD_BOT_TOKEN)
        else:
            run = client.login(settings.DISCORD_BOT_TOKEN)

        asyncio.run_coroutine_threadsafe(run, loop)
        loop.run_forever()

    def run_coroutine(self, coro):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result()

    def bot_initialized(self) -> bool:
        return hasattr(self, 'client')

    def run(self) -> None:
        try:
            return self.run_client()
        except LoginFailure as exc:
            self.log.error('The bot failed to connect to Discord.')
            self.log.critical(exc)
            if exc.__cause__:
                self.log.critical(exc.__cause__)

    def join(self, timeout: Optional[float] = None) -> None:
        if hasattr(self, 'client'):
            self.loop.run_until_complete(self.client.close())
            self.loop.close()
        return super().join(timeout=timeout)
