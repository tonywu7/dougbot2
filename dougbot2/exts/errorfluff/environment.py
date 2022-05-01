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
from typing import Optional

from discord.ext.commands import Context
from more_itertools import always_iterable

from ...blueprints import (
    ErrorPage, _ExceptionHandler, _ExceptionResult, _ExceptionType,
)
from ...utils.datastructures import TypeDictionary

Blurbs = TypeDictionary[type[Exception], Optional[_ExceptionHandler]]
Fluff = TypeDictionary[type[Exception], set[str]]


class Errorfluff(ErrorPage):
    """Centralized object managing error messages."""

    def __init__(self):
        self.blurbs: Blurbs = TypeDictionary()
        self.fluff: Fluff = TypeDictionary()

    def set_error_blurb(self, exc: _ExceptionType, blurb: _ExceptionHandler) -> None:
        self.blurbs[exc] = blurb

    def add_error_fluff(self, exc: _ExceptionType, *fluff: str) -> None:
        for type_ in always_iterable(exc):
            if not self.fluff.contains_exact(type_):
                self.fluff[type_] = set(fluff)
            else:
                self.fluff[type_].update(fluff)

    async def get_error(self, ctx: Context, exc: Exception) -> Optional[_ExceptionResult]:
        """Process the exception and return a dict convertible to an embed."""
        printer = self.blurbs.get(type(exc))
        if not printer:
            return
        error = await printer(ctx, exc)
        if not error:
            return
        reply = random.choice([*self.fluff[type(exc)]])
        return {'title': reply, 'description': error}

    @classmethod
    async def exception_to_str(cls, ctx: Context, exc: Exception) -> str:
        return str(exc)
