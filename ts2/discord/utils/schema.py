# schema.py
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

import re

from graphene import InputObjectType, List, ObjectType


def _rename_to_input(s: str) -> str:
    return re.sub(r'(?:Type)?$', 'Input', s, 1)


def input_from_type(t: type[ObjectType], **overrides) -> type[InputObjectType]:
    __dict__ = {k: v for k, v in overrides.items() if v}

    for k, v in t._meta.fields.items():
        if overrides.get(k) is False:
            continue
        field_t = v._type
        if isinstance(field_t, List):
            __dict__[k] = List(field_t.of_type)
        else:
            __dict__[k] = v.type()

    return type(_rename_to_input(t.__name__), (InputObjectType,), __dict__)
