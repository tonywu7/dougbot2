# util.py
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

from operator import itemgetter
from typing import Literal, get_args, get_origin


def unpack_varargs(item: tuple, names: list[str], **defaults):
    if not isinstance(item, tuple):
        item = (item,)
    unpacked = {**defaults, **dict(zip(names, item))}
    for k in unpacked:
        v = unpacked[k]
        if get_origin(v) is Literal:
            unpacked[k] = get_args(v)
    return itemgetter(*names)(unpacked)
