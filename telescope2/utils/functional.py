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

import pickle
from functools import wraps
from hashlib import sha256
from types import MethodType

from django.core.cache import caches

from .importutil import objpath

_MISS = object()


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
