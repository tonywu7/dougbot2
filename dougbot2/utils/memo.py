# memo.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

from functools import partial
from typing import Any, Callable, TypeVar

_MISS = object()

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E", bound=Callable)


def memoize(obj: object, k: str, *args, factory=list, setter=list.append):
    """Memoize metadata about a function so that decorators can be applied in arbitrary orders."""
    memo: list
    try:
        memo = getattr(obj, k)
    except AttributeError:
        memo = factory()
        setattr(obj, k, memo)
    setter(memo, *args)
    return obj


dict_memoize = partial(memoize, factory=dict, setter=dict.__setitem__)


def get_memo(obj, k: str, *members: str, default: T) -> T:
    """Get a previously memoized attribute from an object."""
    memo = getattr(obj, k, _MISS)
    if memo is not _MISS:
        return memo
    for attr in members:
        try:
            member = getattr(obj, attr)
        except AttributeError:
            continue
        memo = getattr(member, k, _MISS)
        if memo is not _MISS:
            return memo
    return default


def memoized_decorator(key: str):
    def wrapper(func: E) -> E:
        decorator_func: E

        def decorator_func(*args: Any, **kwargs: Any):
            memo = func(*args, **kwargs)

            def decorator(obj: Any):
                return memoize(obj, key, memo)

            return decorator

        return decorator_func

    return wrapper
