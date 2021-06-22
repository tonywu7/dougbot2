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
from contextlib import contextmanager
from typing import (Any, ContextManager, Coroutine, Dict, Generic, Optional,
                    Type, TypeVar)

from discord import Client
from discord.errors import LoginFailure
from discord.ext.commands import Bot
from django.conf import settings

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)


class BotRunner(threading.Thread, Generic[T]):
    def __init__(self, client_cls: Type[T], client_opts: Dict,
                 run_forever=True, standby=False,
                 *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger('discord.runner')

        self._client_cls = client_cls
        self._client_options = client_opts
        self._run_forever = run_forever
        self._standby = standby

        self.loop: asyncio.AbstractEventLoop
        self.client: T

        self.bot_init = threading.Condition()
        self.data_requested = threading.Condition()
        self.data_ready = threading.Condition()

        self._request: Coroutine
        self._data: Any

    def get_client(self) -> T:
        return self._client_cls(**self._client_options)

    def run_client(self):
        with self.bot_init:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = self._client_cls(loop=loop, **self._client_options)
            self.loop = loop
            self.client = client
            self.bot_init.notify_all()

        if self._run_forever:
            loop.create_task(client.start(settings.DISCORD_BOT_TOKEN))
            loop.run_forever()

        elif self._standby:
            loop.run_until_complete(client.login(settings.DISCORD_BOT_TOKEN))
            self._listen()

    def _listen(self):
        while True:
            with self.data_requested:
                self.data_requested.wait_for(self.has_request)
            try:
                self._data = self.loop.run_until_complete(self._request)
            except Exception as e:
                self._data = e
            with self.data_ready:
                self.data_ready.notify_all()
                self.del_request()

    def set_request(self, coro: Coroutine):
        self._request = coro

    def del_request(self):
        try:
            del self._request
        except AttributeError:
            pass

    def has_request(self):
        return hasattr(self, '_request')

    def has_result(self):
        return hasattr(self, '_data')

    def get_result(self):
        data = self._data
        del self._data
        return data

    def run_coroutine(self, coro):
        with self.data_requested:
            self.set_request(coro)
            self.data_requested.notify_all()
        with self.data_ready:
            self.data_ready.wait_for(self.has_result)
            result = self.get_result()
        if isinstance(result, Exception):
            raise result
        return result

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

    @classmethod
    @contextmanager
    def instanstiate(cls, client_cls: Type[U], *args, run_forever=False, daemon=True, **kwargs) -> ContextManager[U]:
        thread = cls(client_cls, *args, run_forever=False, daemon=True, **kwargs)
        thread.start()
        with thread.bot_init:
            thread.bot_init.wait_for(thread.bot_initialized)
        try:
            yield thread.client
        finally:
            thread.join()
