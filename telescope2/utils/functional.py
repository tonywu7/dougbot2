# functional.py
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

import pickle
from functools import wraps
from hashlib import sha256
from inspect import isfunction
from types import MethodType
from typing import Callable, Generic, List, TypeVar

from django.core.cache import caches

from .importutil import objpath

_MISS = object()

T = TypeVar('T')
U = TypeVar('U')

Wrapper = Callable[[T], U]
Decorator = Callable[..., Wrapper[T, U]]


def _sha256digest(b: bytes):
    return sha256(b).hexdigest()


def persistent_hash(func, args, kwargs, algorithm=_sha256digest) -> str:
    name = objpath(func)
    return algorithm(pickle.dumps((name, args, kwargs)))


def acached(cache_id: str, ttl: int = 600):
    def wrapper(f):
        @wraps(f)
        async def wrapped(*args, **kwargs):
            cache = caches[cache_id]
            key = persistent_hash(f, args, kwargs)
            cached_result = cache.get(key, _MISS)
            if cached_result is not _MISS:
                return cached_result
            result = await f(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        return wrapped
    return wrapper


def cached(cache_id: str, ttl: int = 600):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            cache = caches[cache_id]
            key = persistent_hash(f, args, kwargs)
            cached_result = cache.get(key, _MISS)
            if cached_result is not _MISS:
                return cached_result
            result = f(*args, **kwargs)
            cache.set(key, result, ttl)
            return result
        return wrapped
    return wrapper


def evict(cache_id: str, func, *args, **kwargs):
    if isinstance(func, MethodType):
        args = (func.__self__, *args)
        func = func.__func__
    caches[cache_id].delete(persistent_hash(func, args, kwargs))


class ReverseDecorator(Generic[T, U]):
    def __init__(self, initial: T):
        self.initial: T = initial
        self.stack: List[Wrapper[T, U]] = []

    def apply(self) -> U:
        obj = self.initial
        for wrapper in reversed(self.stack):
            obj = wrapper(obj)
        return obj


def _ensure_proxy(f: T | ReverseDecorator[T, U]) -> ReverseDecorator[T, U]:
    if not isinstance(f, ReverseDecorator):
        return ReverseDecorator(f)
    return f


def deferred(deco_func: Decorator[T, U]) -> Decorator[T | ReverseDecorator[T, U], ReverseDecorator[T, U]]:
    def make_decorator(deco_func: Decorator[T, U]):
        def decorated(*args, **kwargs):
            wrapper: Wrapper[T, U] = deco_func(*args, **kwargs)
            def substitute(f: T | ReverseDecorator[T, U]) -> ReverseDecorator[T, U]:  # noqa: E306
                proxy = _ensure_proxy(f)
                proxy.stack.append(wrapper)
                return proxy
            return substitute
        return decorated

    if not isfunction(deco_func):
        return make_decorator
    return make_decorator(deco_func)


def finalizer(deco_func: Decorator[T, U]) -> Decorator[ReverseDecorator[T, U], U]:
    def make_decorator(deco_func: Decorator[T, U]):
        def decorated(*args, **kwargs) -> U:
            wrapper: Wrapper[T, U] = deco_func(*args, **kwargs)
            def substitute(proxy: ReverseDecorator[T, U]) -> U:  # noqa: E306
                proxy = _ensure_proxy(proxy)
                proxy.stack.append(wrapper)
                return proxy.apply()
            return substitute
        return decorated

    if not isfunction(deco_func):
        return make_decorator
    return make_decorator(deco_func)
