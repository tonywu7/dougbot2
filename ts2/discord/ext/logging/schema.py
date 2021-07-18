# schema.py
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

from django.core.exceptions import PermissionDenied
from graphene import List, ObjectType, String

from ...models import Server
from ...utils.graphql import ModelMutation, input_from_type
from .logging import LoggingConfig, can_change, get_name


class LoggingEntryType(ObjectType):
    key: str = String()
    name: str = String()
    channel: str = String()
    role: str = String()


LoggingEntryInput = input_from_type(LoggingEntryType)


class LoggingMutation(ModelMutation[Server], model=Server):
    class Arguments:
        config = List(LoggingEntryInput)

    logging = List(LoggingEntryType)

    @classmethod
    def validate_permission(cls, user, changes: list[LoggingEntryInput]):
        for change in changes:
            if not can_change(user, change.key):
                raise PermissionDenied()

    @classmethod
    def apply(cls, logging: LoggingConfig, changes: list[LoggingEntryInput]):
        logging = {**logging}
        for change in changes:
            key = change.key
            if not change.channel:
                logging.pop(key, None)
                continue
            name = get_name(key)
            logging[change.key] = {
                'name': name,
                'channel': int(change.channel),
                'role': int(change.role),
            }
        return logging

    @classmethod
    def mutate(cls, root, info, **arguments):
        user = info.context.user
        with cls.instance(arguments) as server:
            logging = server.logging
            conf = arguments['config']
            cls.validate_permission(user, conf)
            server.logging = cls.apply(logging, conf)
            server.save()
        return cls(logging=resolve_logging(server, info))


def resolve_logging(server: Server, info):
    user = info.context.user
    return [LoggingEntryType(key=k, **v)
            for k, v in server.logging.items()
            if can_change(user, k)]
