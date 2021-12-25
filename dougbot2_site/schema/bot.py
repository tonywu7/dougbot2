# bot.py
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

from django.http import HttpRequest
from graphene import Field, List, ObjectType, String

from ..updater import get_updater
from ..utils.graphql import HasContext


def get_commands(req: HttpRequest) -> list[str]:
    """Get a list of available bot commands to be provided to the web API."""
    superuser = req.user.is_superuser
    bot = get_updater().client
    return [*sorted(
        c.qualified_name for c
        in bot.walk_commands()
        if not bot.manual.is_hidden(c) or superuser
    )]


class BotType(ObjectType):
    commands = List(String)

    @staticmethod
    def resolve_commands(root, info: HasContext, **kwargs):
        return get_commands(info.context)


class BotQuery(ObjectType):
    bot = Field(BotType)

    @classmethod
    def resolve_bot(cls, root, info):
        return BotType()
