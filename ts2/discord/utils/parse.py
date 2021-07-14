# parser.py
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
from types import FunctionType
from typing import Any, Optional, TypeVar

import click
from discord.ext.commands import Command

T = TypeVar('T')


def option(
    *names: str,
    type_: Optional[Callable[[str], T]] = None,
    required: bool = False,
    default: Optional[str | T] = None,
    nargs: Optional[int] = None,
    multiple: bool = False,
    metavar: Optional[str] = None,
    is_flag: Optional[bool] = None,
    flag_value: Optional[Any] = None,
    count: bool = False,
):
    opt = click.Option(
        names,
        type=type_,
        required=required,
        default=default,
        nargs=nargs,
        multiple=multiple,
        metavar=metavar,
        is_flag=is_flag,
        flag_value=flag_value,
        count=count,
    )

    def wrapper(f: Command | FunctionType):
        cmd: click.Command
        try:
            name = f.name
        except AttributeError:
            name = f.__name__
        try:
            cmd = f.__click__
        except AttributeError:
            cmd = f.__click__ = click.Command(name)
        cmd.params.append(opt)
        return f
    return wrapper


def build_parser(f: Command):
    cmd: click.Command = getattr(f, '__click__', None)
    if not cmd:
        cmd = getattr(f._callback, '__click__', None)
    if not cmd:
        return
    for opt in cmd.params:
        del f.params[opt.name]
