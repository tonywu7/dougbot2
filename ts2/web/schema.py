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

from graphene import ObjectType, Schema

from ts2.discord.contrib.schema import InternetMutation, InternetQuery
from ts2.discord.schema import (ACLMutation, ACLQuery, BotQuery,
                                LoggingMutation, LoggingQuery, ServerMutation,
                                ServerQuery)


class Query(
    ServerQuery, BotQuery,
    LoggingQuery, ACLQuery,
    InternetQuery,
    ObjectType,
):
    pass


class Mutation(
    ServerMutation,
    LoggingMutation, ACLMutation,
    InternetMutation,
    ObjectType,
):
    pass


schema = Schema(query=Query, mutation=Mutation)
