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

from typing import Protocol

from django.urls import ResolverMatch
from django.utils.datastructures import MultiValueDict
from graphene import Field, ObjectType, Schema
from graphene_django import DjangoListField

from ts2.discord.models import Server
from ts2.discord.schema import BotCommandType, ServerType

from .middleware import DiscordContext
from .models import User


class RequestContext(Protocol):
    GET: MultiValueDict
    POST: MultiValueDict
    META: MultiValueDict
    user: User
    resolver_match: ResolverMatch

    def get_ctx() -> DiscordContext:
        ...


class HasContext(Protocol):
    context: RequestContext


class ServerQuery(ObjectType):
    server = Field(ServerType)

    def resolve_server(self, info):
        snowflake = info.context.resolver_match.kwargs['guild_id']
        return Server.objects.get(snowflake=snowflake)


class PublicQuery(ObjectType):
    commands = DjangoListField(BotCommandType)


server_schema = Schema(query=ServerQuery)
public_schema = Schema(query=PublicQuery)
