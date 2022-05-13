# fields.py
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

from collections.abc import Iterable, Mapping
from typing import Optional, Union

import discord
from django.db import models

from .duckcord import Color2, Permissions2


class PermissionField(models.BigIntegerField):
    """Django integer field representing a discord.py Permissions object."""

    def to_python(self, value) -> Union[discord.Permissions, None]:
        number = super().to_python(value)
        if number is None:
            return None
        return Permissions2(number)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_prep_value(self, value: Union[discord.Permissions, Permissions2, None]):
        if value is None:
            return super().get_prep_value(None)
        elif isinstance(value, discord.Permissions):
            return super().get_prep_value(value.value)
        return super().get_prep_value(int(value))


class ColorField(models.IntegerField):
    """Django integer field representing a discord.py Color object."""

    def to_python(self, value) -> Union[Color2, None]:
        number = super().to_python(value)
        if number is None:
            return None
        return Color2(number)

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def get_prep_value(self, value: Union[discord.Color, Color2]):
        if value is None:
            return super().get_prep_value(None)
        elif isinstance(value, discord.Colour):
            return super().get_prep_value(value.value)
        return super().get_prep_value(int(value))


class NumbersListField(models.JSONField):
    """A subclass of JSONField that ensures the data can only be an array of numbers."""

    def from_db_value(self, value, expression, connection):
        struct = super().from_db_value(value, expression, connection)
        if not isinstance(struct, Iterable):
            return None
        return [int(s) for s in struct]

    def get_prep_value(self, value: Optional[list[int]]):
        if not isinstance(value, Iterable):
            return super().get_prep_value(None)
        return super().get_prep_value([int(s) for s in value])


class RecordField(models.JSONField):
    """A subclass of JSONField that ensures the data can only be a single-level\
    string to string mapping."""

    def from_db_value(self, value, expression, connection):
        struct = super().from_db_value(value, expression, connection)
        if not isinstance(struct, dict):
            return None
        return {str(k): str(v) for k, v in struct.items()}

    def get_prep_value(
        self, value: Optional[Union[dict[str, str], list[tuple[str, str]]]]
    ):
        if isinstance(value, Mapping):
            value = value.items()
        elif not isinstance(value, Iterable):
            return super().get_prep_value(None)
        result = {str(k): str(v) for k, v in value}
        return super().get_prep_value(result)
