# ipc.py
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
from collections import defaultdict
from collections.abc import Callable, Coroutine

from django.core.cache import caches

AsyncCallback = Callable[[str], Coroutine]


class EventTarget:
    def __init__(self):
        self._lock = threading.Lock()
        self.listeners: dict[str, dict[AsyncCallback, None]] = defaultdict(dict)

    def add_event_listener(self, event: str, callback: Callable[[str], AsyncCallback]):
        with self._lock:
            self.listeners[event][callback] = None

    def remove_event_listener(self, event: str, callback: Callable[[str], AsyncCallback]):
        with self._lock:
            self.listeners[event].pop(callback, None)


class CachePollingThread(EventTarget, threading.Thread):
    def __init__(self, cache: str, interval: float = 5.0, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        EventTarget.__init__(self)
        self.cache_id = cache
        self.interval = interval
        self.log = logging.getLogger('eventlistener')

    def run(self):
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self.poll())
        except KeyboardInterrupt:
            loop.stop()

    async def poll(self):
        while True:
            await asyncio.sleep(self.interval)
            await self.check()

    async def check(self):
        cache = caches[self.cache_id]
        with self._lock:
            events = {k: [*v] for k, v in self.listeners.items()}
        for event, listeners in events.items():
            if cache.get(event, None):
                cache.delete(event)
                tasks = [ls(event) for ls in listeners]
                res = await asyncio.gather(*tasks, return_exceptions=True)
                for r in res:
                    if isinstance(r, Exception):
                        self.log.error(r, exc_info=r)
