# decorators.py
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

import logging
from typing import Optional

from .logging import bypassed, exceptions, logging_classes, privileged


def log_exception(
    name: str, key: Optional[str] = None,
    level: int = logging.ERROR,
    superuser: bool = False,
):
    """Add a log config entry for the decorated Exception class.

    :param name: The title of the log message
    :type name: str
    :param key: A unique name for the log config, defaults to None,
    in which case the exception's class name is used
    :type key: Optional[str], optional
    :param level: The logging level for this exception, defaults to logging.ERROR;
    this affects the behavior when logging the stderr, which uses the logging module
    :type level: int, optional
    :param superuser: Whether the config for this exception should
    only be visible to superusers on the website, defaults to False
    :type superuser: bool, optional
    """
    def wrapper(exc: type[Exception], key=key):
        key = key or exc.__name__
        if key in exceptions:
            raise ValueError(f'A logger for {key} has already been registered.')
        exceptions[key] = {
            'exc': (exc,),
            'name': name,
            'level': level,
            'superuser': superuser,
        }
        logging_classes[key] = name
        if superuser:
            privileged.add(key)
        return exc
    return wrapper


def ignore_exception(exc: type[Exception]):
    """Ignore this exception so that it is never logged."""
    bypassed.add(exc)
    return exc
