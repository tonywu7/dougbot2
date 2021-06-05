# client.py
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
import threading
from typing import Dict, Type

from discord import Client
from django.conf import settings

from .bot import Telescope

instance = None
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


def run():
    from .models import BotPrefs

    try:
        prefs = BotPrefs.objects.get(pk=1)
    except BotPrefs.DoesNotExist:
        prefs = BotPrefs()
        prefs.save()

    global thread
    thread = BotThread(Telescope, prefs.to_options(), daemon=True)
    thread.start()

    return prefs


def get_thread():
    return thread


def is_alive() -> bool:
    return thread and thread.is_alive()
