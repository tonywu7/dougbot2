# converters.py
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

import logging
from typing import Union

from discord.ext.commands import Converter


class LoggingLevel(Converter):
    """Convert a logging level name (e.g. DEBUG) to its int value."""

    async def convert(self, ctx, arg: str) -> Union[int, str]:
        level = logging.getLevelName(arg)
        if isinstance(level, int):
            return level
        return arg
