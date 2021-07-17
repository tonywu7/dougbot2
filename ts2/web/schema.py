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

from ts2.discord import schema as discord
from ts2.discord.models import Server


class ServerQuery(ObjectType):
    server = Field(discord.ServerType)

    def resolve_server(self, info):
        snowflake = info.context.resolver_match.kwargs['guild_id']
        return Server.objects.get(snowflake=snowflake)


class PublicQuery(ObjectType):
    server = Field(discord.ServerType)
    bot = Field(discord.BotType)

    def resolve_server(self, info):
        return None

    def resolve_bot(self, info):
        return discord.BotType()


class ServerMutation(ObjectType):
    create = discord.ServerCreateMutation.Field()
    update_prefix = discord.ServerPrefixMutation.Field()
    update_extensions = discord.ServerExtensionsMutation.Field()
    update_models = discord.ServerModelSyncMutation.Field()
    update_logging = discord.ServerLoggingMutation.Field()
    delete_acl = discord.ServerACLDeleteMutation.Field(name='deleteACL')
    update_acl = discord.ServerACLUpdateMutation.Field(name='updateACL')


server_schema = Schema(query=ServerQuery, mutation=ServerMutation)
public_schema = Schema(query=PublicQuery)
