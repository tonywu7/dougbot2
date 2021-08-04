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

from importlib import import_module
from pkgutil import iter_modules
from typing import Generator, List


def objpath(obj):
    return f'{obj.__module__}.{obj.__name__}'


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
    ...     import_module(f'.views.{".".join(path)}', __package__)
    """
    if not depth:
        return
    parts = parts or []
    for modinfo in iter_modules([pkg]):
        path = [*parts, modinfo.name]
        yield path
        if modinfo.ispkg:
            yield from iter_module_tree(f'{pkg}/{modinfo.name}', depth - 1, path)
