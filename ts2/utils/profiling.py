# profiling.py
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

import cProfile
import logging
import time
from contextlib import contextmanager
from functools import wraps

from .importutil import objpath

log = logging.getLogger('util.datetime')


@contextmanager
def cprofile(out: str, enabled: bool = True):
    pr = cProfile.Profile()
    if enabled:
        pr.enable()
    try:
        yield pr
    finally:
        if not enabled:
            pass
        pr.disable()
        pr.dump_stats(out)


def abenchmark(func):
    name = objpath(func)

    @wraps(func)
    async def wrapped(*args, **kwargs):
        start = time.time()
        try:
            return await func(*args, **kwargs)
        finally:
            log.debug(f'Execution time {name} {(time.time() - start) * 1000:.3f}ms')
    return wrapped


def benchmark(func):
    name = objpath(func)

    @wraps(func)
    def wrapped(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            log.debug(f'Execution time {name} {(time.time() - start) * 1000:.3f}ms')
    return wrapped


@contextmanager
def benchmark_block(name):
    start = time.time()
    try:
        yield
    finally:
        log.debug(f'Execution time {name} {(time.time() - start) * 1000:.3f}ms')
