# events.py
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
import time
from collections.abc import Callable, Coroutine, Iterable
from functools import wraps
from typing import Any, Optional, Union

from discord import (Client, Emoji, Forbidden, Member, Message, PartialEmoji,
                     RawReactionActionEvent, User)
from discord.ext.commands import BotMissingPermissions, Context

Decorator = Callable[[Callable], Callable]
EventFilter = Callable[..., Coroutine[Any, Any, bool]]
SyncEventFilter = Callable[..., bool]


def event_filter(ev_filter: EventFilter) -> Decorator:
    def wrapper(f: Callable[..., Coroutine]):
        @wraps(f)
        async def wrapped(*args, **kwargs):
            if await ev_filter(*args, **kwargs):
                return await f(*args, **kwargs)
        return wrapped
    return wrapper


def emote_no_bots(event: RawReactionActionEvent):
    return not event.member or not event.member.bot


def emote_added(event: RawReactionActionEvent):
    return event.event_type == 'REACTION_ADD'


def reaction_from(*ids: int):
    def check(event: RawReactionActionEvent, ids=frozenset(ids)):
        return event.user_id in ids
    return check


def reaction_on(*ids: int):
    def check(event: RawReactionActionEvent, ids=frozenset(ids)):
        return event.message_id in ids
    return check


def emote_matches(*emotes: str | int):
    def check_emote(event: RawReactionActionEvent):
        id_ = event.emoji.id or event.emoji.name
        return id_ in emotes
    return check_emote


class Responder:
    def __init__(self, events: dict[str, Callable[..., bool]],
                 client: Client, ttl: float) -> None:
        self.log = logging.getLogger('discord.responder')
        self.events = events
        self.client = client
        self.ttl = ttl
        self.end: float

    def check(self, event: str, args) -> bool:
        return all(t(args) for t in self.events[event])

    async def on_start(self):
        return True

    async def on_finish(self):
        return

    async def init(self) -> bool:
        try:
            return await self.on_start()
        except Forbidden as e:
            raise BotMissingPermissions([]) from e
        except Exception as e:
            self.log.debug(f'{type(e).__name__} while starting paginator: {e}\n')
            return False

    async def cleanup(self):
        try:
            return await self.on_finish()
        except Exception:
            pass

    async def run(self):
        self.end = time.perf_counter() + self.ttl

        while True:
            ts = time.perf_counter()
            if ts > self.end:
                break
            timeout = self.end - ts
            try:
                listeners = {self.client.wait_for(k, check=t, timeout=timeout)
                             for k, t in self.events.items()}
                done, pending = await asyncio.wait(listeners, return_when=asyncio.FIRST_COMPLETED)
                first = done.pop()
                args = first.result()
            except asyncio.TimeoutError:
                continue

            try:
                stop = await self.handle(args)
            except Exception as e:
                self.log.debug(f'{type(e).__name__} while handling reactions: {e}\n')
            else:
                if stop:
                    break

        await self.cleanup()

    async def handle(self, args: Union[Any, tuple]) -> Optional[bool]:
        raise NotImplementedError

    def __await__(self):
        return self.run()


class EmoteResponder(Responder):
    def __init__(
        self, users: Iterable[int | Member], emotes: list[Emoji | PartialEmoji | str],
        message: Message, *args, **kwargs,
    ) -> None:
        self.message = message
        self.emotes: dict[int | str, str | Emoji | PartialEmoji] = {}
        users = [m.id if isinstance(m, (Member, User)) else m for m in users]
        for e in emotes:
            if isinstance(e, str):
                self.emotes[e] = e
            elif isinstance(e, (Emoji, PartialEmoji)):
                self.emotes[e.id] = e

        def test(evt: RawReactionActionEvent):
            return all(t(evt) for t in (
                emote_no_bots,
                emote_matches(*self.emotes.keys()),
                reaction_from(*users),
                reaction_on(self.message.id),
            ))

        events = {
            'raw_reaction_add': test,
            'raw_reaction_remove': test,
        }
        super().__init__(events, *args, **kwargs)

    async def on_start(self):
        for emote in self.emotes:
            await self.message.add_reaction(emote)
        return True

    async def on_finish(self):
        for emote in self.emotes:
            await self.message.clear_reaction(emote)


class DeleteResponder(EmoteResponder):
    def __init__(self, ctx: Context, message: Message, ttl: int = 300) -> None:
        super().__init__([ctx.author.id], ['🗑'], client=ctx.bot, message=message, ttl=ttl)

    async def handle(self, event) -> True:
        await self.message.delete(delay=.1)
        return True


async def run_responders(*responders: Responder):
    should_run = []
    for r in responders:
        if await r.init():
            should_run.append(r)
    if not should_run:
        return []
    return await asyncio.gather(*should_run, return_exceptions=True)


def start_responders(*responders: Responder):
    loop = asyncio.get_running_loop()

    def run():
        future = asyncio.run_coroutine_threadsafe(run_responders(*responders), loop)
        return future.result()

    thread = threading.Thread(target=run, daemon=True)
    return thread.start()
