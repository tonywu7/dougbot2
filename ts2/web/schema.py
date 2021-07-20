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

from graphene import ID, Field, List, ObjectType, Schema

from ts2.discord import schema as discord
from ts2.discord.ext import schema as discord_ext
from ts2.discord.models import Server

from .middleware import get_server


class Query(ObjectType):
    bot = Field(discord.BotType)
    server = Field(discord.ServerType, item_id=ID(required=True))
    logging = List(discord_ext.LoggingEntryType, item_id=ID(required=True))
    acl = List(discord_ext.AccessControlType, item_id=ID(required=True))

    @classmethod
    def resolve_bot(cls, root, info):
        return discord.BotType()

    @classmethod
    def resolve_server(cls, root, info, item_id) -> Server:
        return get_server(info.context, item_id)

    @classmethod
    def resolve_logging(cls, root, info, item_id):
        server = cls.resolve_server(root, info, item_id)
        return discord_ext.resolve_logging(server, info)

    @classmethod
    def resolve_acl(cls, root, info, item_id):
        server = cls.resolve_server(root, info, item_id)
        return discord_ext.AccessControlType.serialize([*server.acl.all()])


class Mutation(ObjectType):
    update_prefix = discord.ServerPrefixMutation.Field()
    update_extensions = discord.ServerExtensionsMutation.Field()
    update_models = discord.ServerModelSyncMutation.Field()
    update_logging = discord_ext.LoggingMutation.Field()
    delete_acl = discord_ext.ACLDeleteMutation.Field(name='deleteACL')
    update_acl = discord_ext.ACLUpdateMutation.Field(name='updateACL')


schema = Schema(query=Query, mutation=Mutation)
