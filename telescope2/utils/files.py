# files.py
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

import hashlib
from pathlib import Path
from typing import Callable, Generator, List


def file_hash(filepath, blocksize=2**20, hashfunc=hashlib.sha1):
    # From dejavu
    s = hashfunc()
    try:
        with open(filepath, 'rb') as f:
            while True:
                buf = f.read(blocksize)
                if not buf:
                    break
                s.update(buf)
    except OSError:
        pass
    return s.hexdigest()


def file_size(filepath):
    return Path(filepath).stat().st_size


def simple_file_signature(path):
    return (Path(path).stat().st_size, None)


def full_file_signature(path):
    return (Path(path).stat().st_size, file_hash(path))


def find_files(paths: List[Path], *tests: Callable[[Path], bool], depth=1) -> Generator[Path, None, None]:
    if depth <= -1:
        return []
    for p in paths:
        if p.is_file() and all(t(p) for t in tests):
            yield p
        elif p.is_dir():
            try:
                yield from find_files([*p.iterdir()], *tests, depth=depth - 1)
            except PermissionError:
                continue
