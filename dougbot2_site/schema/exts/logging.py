# logging.py
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

from typing import Iterator

from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from graphene import ID, Argument, InputObjectType, List, ObjectType, String

from ...exts.logging.logging import (LoggingEntry, _ErrorConf, exceptions,
                                     get_name, logging_classes, privileged)
from ...middleware import get_ctx
from ...models import Server
from ..server import ServerModelMutation


def has_logging_conf_permission(user: User, key: str) -> bool:
    return (key not in privileged or user.is_superuser)  # Material conditional


def iter_logging_conf(user) -> Iterator[tuple[str, _ErrorConf]]:
    for k in logging_classes.keys() - exceptions.keys():
        yield k, {'name': logging_classes[k]}
    for k, v in exceptions.items():
        if has_logging_conf_permission(user, k):
            yield k, v


def get_logging_conf(req: HttpRequest, server: Server) -> list[LoggingEntry]:
    user = req.user
    return [{'key': k, **{u: w for u, w in v.items() if w}}
            for k, v in server.logging.items()
            if has_logging_conf_permission(user, k)]


def set_logging_conf(req: HttpRequest, server: Server, changes: list):
    user = req.user

    for change in changes:
        if not has_logging_conf_permission(user, change.key):
            raise PermissionDenied('Insufficient permissions.')

    logging = server.logging.copy()

    for change in changes:
        key = change.key
        if not change.channel:
            logging.pop(key, None)
            continue
        name = get_name(key)
        logging[change.key] = {
            'name': name,
            'channel': int(change.channel),
            'role': int(change.role or 0),
        }

    server.logging = logging
    server.save()


class LoggingEntryType(ObjectType):
    key: str = String()
    name: str = String()
    channel: str = String()
    role: str = String()


class LoggingEntryInput(InputObjectType):
    key: str = Argument(String, required=True)
    channel: str = Argument(String, required=True)
    role: str = Argument(String, required=True)


class LoggingUpdateMutation(ServerModelMutation):
    class Meta:
        model = Server

    class Arguments:
        config = Argument(List(LoggingEntryInput), default_value=())

    logging = List(LoggingEntryType)

    @classmethod
    def mutate(cls, root, info, *, server_id: str, config: list[LoggingEntryInput]):
        req = info.context
        server = cls.get_instance(req, server_id)
        set_logging_conf(req, server, config)
        return cls(logging=get_logging_conf(req, server))


class LoggingQuery(ObjectType):
    logging = List(LoggingEntryType, server_id=ID(required=True))

    @classmethod
    def resolve_logging(cls, root, info, server_id):
        server = get_ctx(info.context).fetch_server(server_id, 'read')
        return get_logging_conf(info.context, server)


class LoggingMutation(ObjectType):
    update_logging = LoggingUpdateMutation.Field()
