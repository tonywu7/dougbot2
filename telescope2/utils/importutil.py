# importutil.py
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

from importlib import import_module
from pkgutil import iter_modules
from typing import Generator, List


def objpath(obj):
    return f'{obj.__module__}.{obj.__qualname__}'


def load_object(qualname: str):
    parts = qualname.split('.')
    mod, funcname = '.'.join(parts[:-1]), parts[-1]
    func = getattr(import_module(mod), funcname)
    return func


def iter_module_tree(pkg: str, depth: int = 1, parts: List[str] = None) -> Generator[List[str], None, None]:
    """Recursively iterate over an import path yielding subpackages.

    Parameters
    ----------
    pkg : str
        Filesystem path of the module to iterate, e.g. `str(Path(__file__).with_name('views'))`
    depth : int, optional
        Search depth, 1 will find all immediate subpackages of a module, by default 1

    Yields
    -------
    Generator[List[str], None, None]
        Lists of qualified name components not including the root module that is searched

    Examples
    --------
    >>> for parts in iter_module_tree(str(Path(__file__).with_name('views')), 2):
    ...     import_module(f'.views.{".".join(parts)}', __package__)
    """
    if not depth:
        return
    parts = parts or []
    for modinfo in iter_modules([pkg]):
        path = [*parts, modinfo.name]
        yield path
        if modinfo.ispkg:
            yield from iter_module_tree(f'{pkg}/{modinfo.name}', depth - 1, path)
