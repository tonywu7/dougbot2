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

from discord import Role
from discord.ext.commands import Converter
from discord.ext.commands.errors import BadArgument
from duckcord.permissions import Permissions2

from ..autodoc import accepts


@accepts('permission name')
class PermissionName(Converter):
    """Ensure the argument is a valid Discord permission.

    Accepts all flag attributes from the `Permissions` class;
    additionally accepts names where `guild` is replaced with `server`.

    Converter keeps the converted perm name and returns itself.
    """

    perm_name: str

    async def convert(self, ctx, arg: str) -> Callable[[Role], bool]:
        # FIXME: annotation
        if not hasattr(Permissions2, arg):
            if not hasattr(Permissions2, arg.replace('server', 'guild')):
                raise BadArgument(f'No such permission {arg}')
            else:
                arg = arg.replace('server', 'guild')
        self.perm_name = arg
        return self

    def __str__(self):
        return self.perm_name

    def get(self):
        """Get a `discord.Permissions` object with none but this permission set to True."""
        return Permissions2(**{self.perm_name: True})
