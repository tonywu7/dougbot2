# environment.py
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

import random
from typing import Callable, Coroutine, Optional

from discord.ext.commands import Context

from ...utils.datastructures import TypeDictionary

ExceptionHandler = Callable[
    [Context, Exception],
    Coroutine[None, None, Optional[str]],
]

ErrorDict = TypeDictionary[type[Exception], Optional[ExceptionHandler]]
ReplyDict = TypeDictionary[type[Exception], set[str]]


class Environment:
    """Centralized object managing error messages."""

    def __init__(self, errors: ErrorDict, replies: ReplyDict):
        self.errors: ErrorDict = errors or TypeDictionary()
        self.replies: ReplyDict = replies or TypeDictionary()

    def merge(self, *envs: Environment):
        """Include error handlers and error replies from other environments."""
        for env in envs:
            self.errors._dict.update(env.errors._dict)
            for exc, replies in env.replies._dict.items():
                try:
                    self.replies._dict[exc].update(replies)
                except KeyError:
                    self.replies[exc] = replies

    async def get_error(self, ctx: Context, exc: Exception) -> Optional[dict]:
        """Process the exception and return a dict convertible to an embed."""
        printer = self.errors.get(type(exc))
        if not printer:
            return
        error = await printer(ctx, exc)
        if not error:
            return
        reply = random.choice([*self.replies[type(exc)]])
        return {'title': reply, 'description': error}
