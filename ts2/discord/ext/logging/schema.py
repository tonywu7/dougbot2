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

from graphene import Argument, InputObjectType, List, ObjectType, String

from ...models import Server
from ...schema import ServerMutation
from .logging import get_logging_conf, set_logging_conf


class LoggingEntryType(ObjectType):
    key: str = String()
    name: str = String()
    channel: str = String()
    role: str = String()


class LoggingEntryInput(InputObjectType):
    key: str = Argument(String, required=True)
    channel: str = Argument(String, required=True)
    role: str = Argument(String, required=True)


class LoggingMutation(ServerMutation):
    class Meta:
        model = Server

    class Arguments:
        config = Argument(List(LoggingEntryInput), default_value=())

    logging = List(LoggingEntryType)

    @classmethod
    def mutate(cls, root, info, *, item_id: str, config: list[LoggingEntryInput]):
        req = info.context
        server = cls.get_instance(req, item_id)
        set_logging_conf(req, server, config)
        return cls(logging=get_logging_conf(req, server))
