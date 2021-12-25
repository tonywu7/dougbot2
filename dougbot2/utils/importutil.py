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
from pkgutil import walk_packages
from types import ModuleType
from typing import Callable, Generator, Optional, TypeVar

from django.apps import apps

T = TypeVar('T')


def objpath(obj):
    """Return the module path and type name of an object as a fully-qualified name."""
    return f'{obj.__module__}.{obj.__qualname__}'


def getattr_submodules(
    root: ModuleType, name: str,
    validator: Callable[[Optional[T]], bool],
) -> Generator[tuple[str, T], None, None]:
    """Look for objects with the specified in all submodules of a package.

    :param root: The package under which to search for objects.
    :type root: ModuleType
    :param name: The name to access for each imported submodule.
    :type name: str
    :param validator: A function to validate the object; receives the object and
    should return `True` if the object is acceptable; if there is no object
    in a submodule with this name, the function receives `None`.
    :type validator: Callable[[Optional[T]], bool]
    :yield: A 2-tuple of the fully-qualified name of the imported submodule, and the
    accessed item.
    :rtype: Generator[tuple[str, T], None, None]
    """
    for module in walk_packages(root.__path__, f'{root.name}.'):
        imported = import_module(module.name)
        item = getattr(imported, name, None)
        if validator(item):
            yield module.name, item


def get_submodule_from_apps(name: str):
    """Find all submodules with this name under installed Django apps.

    For example, with these as the list of Django apps:

    - `poll`
    - `alarm`
    - `contrib.wiki`

    `find_submodules('urls')` will try to import the following packages,
    if they exist:

    - `poll.urls`
    - `alarm.urls`
    - `contrib.wiki.urls`

    :param name: The relative name to look for
    :type name: str
    :yield: A tuple (app config, submodule)
    :rtype: tuple[CommandAppConfig, ModuleType]
    """
    for app in apps.get_app_configs():
        try:
            yield (app, import_module(f'{app.module.__name__}.{name}'))
        except ModuleNotFoundError:
            continue
