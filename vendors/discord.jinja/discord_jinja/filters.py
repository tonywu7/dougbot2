# MIT License
#
# Copyright (c) 2021 @tonyzbf +https://github.com/tonyzbf/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from datetime import datetime
from collections.abc import Callable

import pytz
from jinja2 import Environment

_filters: dict[str, Callable] = {}


def _register(path: list[str]):
    def wrapper(cls):
        for name, func in vars(cls).items():
            filter_name = name.removeprefix('f_')
            if filter_name == name:
                continue
            filter_name = '.'.join([*path, filter_name])
            _filters[filter_name] = func
        return cls
    return wrapper


@_register(())
class BuiltinFilters:
    def f_bin(value) -> str:
        return bin(value)

    def f_hex(value) -> str:
        return hex(value)


@_register(('time',))
class DatetimeFilters:
    def f_astimezone(value: datetime, timezone: str) -> datetime:
        tz = pytz.timezone(timezone)
        if value.tzinfo:
            return value.astimezone(tz)
        else:
            return tz.localize(value)

    def f_iso8601(value: str) -> datetime:
        return datetime.fromisoformat(value)


def register_filters(env: Environment):
    env.filters.update(_filters)
