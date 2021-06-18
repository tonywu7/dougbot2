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

from functools import wraps
from typing import Any, Callable, Coroutine

from discord import RawReactionActionEvent

Decorator = Callable[[Callable], Callable]
EventFilter = Callable[..., Coroutine[Any, Any, bool]]


class Events:

    @staticmethod
    def event_filter(ev_filter: EventFilter) -> Decorator:
        def wrapper(f: Callable[..., Coroutine]):
            @wraps(f)
            async def wrapped(*args, **kwargs):
                if await ev_filter(*args, **kwargs):
                    return await f(*args, **kwargs)
            return wrapped
        return wrapper

    @staticmethod
    async def emote_no_bots(event: RawReactionActionEvent):
        return event.member and not event.member.bot

    @staticmethod
    async def emote_added(event: RawReactionActionEvent):
        return event.event_type == 'REACTION_ADD'

    @staticmethod
    def emote_matches(*emotes: str | int):
        async def check_emote(event: RawReactionActionEvent):
            id_ = event.emoji.id or event.emoji.name
            return id_ in emotes
        return check_emote
