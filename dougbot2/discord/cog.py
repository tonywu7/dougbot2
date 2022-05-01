# extension.py
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

from discord.ext.commands import Cog, CogMeta

from ..blueprints import MissionControl


class GearMeta(CogMeta):
    """Subclass of `discord.ext.commands.CogMeta` with arbitrary sort order."""

    def __new__(cls, *args, order: int = 50, hidden: bool = False, **kwargs):
        new_cls = super().__new__(cls, *args, **kwargs)
        new_cls.label = cls.__name__.lower()
        new_cls.sort_order = order
        new_cls.hidden = hidden
        return new_cls


class Gear(Cog, metaclass=GearMeta):
    """Subclass of `discord.ext.commands.Cog` with type annotations and a default logger."""

    label: str
    sort_order: int
    hidden: bool

    bot: MissionControl

    def __init__(self, bot: MissionControl) -> None:
        super().__init__()
        self.bot = bot
