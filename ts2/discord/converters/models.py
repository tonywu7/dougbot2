# models.py
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

from collections.abc import Callable
from typing import Optional, overload

from discord import Member, Permissions, Role
from discord.abc import GuildChannel
from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument

from ..context import Circumstances
from ..documentation import accepts
from ..utils.models import HypotheticalRole


@accepts('permission name', predicative=('see [this page](https://discordpy.readthedocs.io/en/'
                                         'stable/api.html#discord.Permissions) for a list'))
class PermissionName(Converter):
    perm_name: str

    async def convert(self, ctx: Circumstances, arg: str) -> Callable[[Role], bool]:
        if not hasattr(Permissions, arg):
            if not hasattr(Permissions, arg.replace('server', 'guild')):
                raise BadArgument(f'No such permission {arg}')
            else:
                arg = arg.replace('server', 'guild')
        self.perm_name = arg
        return self

    def __str__(self):
        return self.perm_name

    @overload
    def __call__(self, entity: Role, channel: None) -> bool:
        ...

    @overload
    def __call__(self, entity: Member, channel: None) -> bool:
        ...

    @overload
    def __call__(self, entity: Member, channel: GuildChannel) -> bool:
        ...

    def __call__(self, entity: Role | Member, channel: Optional[GuildChannel] = None) -> bool:
        if channel:
            return getattr(channel.permissions_for(entity), self.perm_name)
        if isinstance(entity, Member):
            entity = HypotheticalRole(*entity.roles)
        return entity.permissions.administrator or getattr(entity.permissions, self.perm_name)
