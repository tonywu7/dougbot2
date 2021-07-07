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
from functools import reduce
from typing import Any, Optional

from discord import Member, Permissions, Role
from discord.utils import SnowflakeList
from more_itertools import flatten

PERM_GETTER: dict[type, Callable[[Any], Permissions]] = {
    Permissions: lambda x: x,
    Role: lambda x: x.permissions,
    Member: lambda x: x.guild_permissions,
}


class HypotheticalRole:
    def __init__(self, *subjects: Permissions | Role | Member, snowflake: Optional[int] = None, **kwargs) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.id = snowflake or -1
        perms = [PERM_GETTER[type(s)](s) for s in subjects]
        self.permissions = perm_union(*perms)


class HypotheticalMember:
    def __init__(self, *subjects: Role | Member, snowflake: Optional[int] = None, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        self.id = snowflake or -1
        self._roles = SnowflakeList([*flatten([
            [s.id] if isinstance(s, Role) else [r.id for r in s.roles]
            for s in subjects
        ])], is_sorted=False)
        self._role_objs = subjects


def perm_union(*perms: Permissions) -> Permissions:
    return reduce(lambda x, y: Permissions(x.value | y.value), perms, Permissions.none())


def perm_intersection(*perms: Permissions) -> Permissions:
    return reduce(lambda x, y: Permissions(x.value & y.value), perms, Permissions.all())


def perm_complement(perm: Permissions) -> Permissions:
    return Permissions(~perm.value)
