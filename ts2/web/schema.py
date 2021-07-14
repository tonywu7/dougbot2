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

from graphene import Field, ObjectType, Schema
from graphene_django import DjangoListField

from ts2.discord import schema as discord_schema
from ts2.discord.models import Server


class ServerQuery(ObjectType):
    server = Field(discord_schema.ServerType)

    def resolve_server(self, info):
        snowflake = info.context.resolver_match.kwargs['guild_id']
        return Server.objects.get(snowflake=snowflake)


class ServerMutation(ObjectType):
    create = discord_schema.ServerCreateMutation.Field()
    update_prefix = discord_schema.ServerPrefixMutation.Field()
    update_extensions = discord_schema.ServerExtensionsMutation.Field()
    update_models = discord_schema.ServerModelSyncMutation.Field()
    update_logging = discord_schema.ServerLoggingMutation.Field()


class PublicQuery(ObjectType):
    commands = DjangoListField(discord_schema.BotCommandType)


server_schema = Schema(query=ServerQuery, mutation=ServerMutation)
public_schema = Schema(query=PublicQuery)
