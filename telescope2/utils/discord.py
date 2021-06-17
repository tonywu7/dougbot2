# discord.py
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

from functools import reduce
from io import StringIO
from typing import Any, Callable, Dict, Optional, Type

from discord import Color, Member, Permissions, Role
from discord.abc import GuildChannel, User
from discord.ext.commands import Context
from discord.utils import SnowflakeList
from markdown import Markdown
from more_itertools import flatten

PERM_GETTER: Dict[Type, Callable[[Any], Permissions]] = {
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
    return Permissions(reduce(lambda x, y: x.value | y.value, perms, Permissions.none()))


def perm_intersection(*perms: Permissions) -> Permissions:
    return Permissions(reduce(lambda x, y: x.value & y.value, perms, Permissions.all()))


def perm_complement(perm: Permissions) -> Permissions:
    return Permissions(~perm.value)


def trimmed_msg(ctx: Context) -> str:
    return ctx.message.content[len(ctx.prefix) + len(ctx.command.name) + 1:]


def tag(obj) -> str:
    if isinstance(obj, User):
        return f'<@{obj.id}>'
    if isinstance(obj, GuildChannel):
        return f'<#{obj.id}>'
    if isinstance(obj, Role):
        if obj.is_default():
            return '@everyone'
        return f'<@&{obj.id}>'


def traffic_light(val: bool | None, strict=False):
    if val:
        return '🟢'
    elif strict and val is None:
        return '🟡'
    else:
        return '⛔'


def color_to_rgb8(c: Color) -> int:
    return c.value


def unmark_element(element, stream=None):
    # https://stackoverflow.com/a/54923798/10896407
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


Markdown.output_formats['plain'] = unmark_element
_md = Markdown(output_format='plain')
_md.stripTopLevelTags = False


def unmarked(text: str) -> str:
    return _md.convert(text)
