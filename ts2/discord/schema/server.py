# server.py
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
from graphene import (ID, Argument, Boolean, Enum, Field, List, NonNull,
                      ObjectType, String)
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field

from .. import forms
from ..middleware import get_ctx
from ..models import Channel, ChannelTypeEnum, PermissionField, Role, Server
from ..thread import get_thread
from ..utils.graphql import FormMutationMixin, HasContext, ModelMutation
from ..utils.markdown import sized

ChannelTypeEnum = Enum.from_enum(ChannelTypeEnum)


@convert_django_field.register(PermissionField)
def convert_perm_field(field, *args, **kwargs):
    return List(NonNull(String), required=not field.null)


class DiscordObject:
    snowflake = NonNull(ID)


class EmoteType(DiscordObject, ObjectType):
    name = NonNull(String)
    animated = NonNull(Boolean)
    url = NonNull(String)
    thumbnail = NonNull(String)


class ServerType(DiscordObject, DjangoObjectType):
    extensions = List(String)
    readable = List(NonNull(ID))
    writable = List(NonNull(ID))

    emotes = List(NonNull(EmoteType))

    class Meta:
        model = Server
        fields = (
            'prefix', 'disabled',
            'name', 'perms',
            'channels', 'roles',
        )

    @staticmethod
    def resolve_extensions(obj: Server, *args, **kwargs):
        return obj.extensions

    @staticmethod
    def resolve_emotes(obj: Server, *args, **kwargs):
        bot = get_thread().client
        guild = bot.get_guild(obj.snowflake)
        if not guild:
            return []
        emotes = [EmoteType(snowflake=e.id, name=e.name,
                            animated=e.animated, url=e.url,
                            thumbnail=sized(str(e.url_as(format='png')), 64))
                  for e in guild.emojis]
        return emotes


class ChannelType(DiscordObject, DjangoObjectType):
    type = ChannelTypeEnum(source='type')

    class Meta:
        model = Channel
        fields = ('snowflake', 'name', 'guild', 'order', 'category')


class RoleType(DiscordObject, DjangoObjectType):
    class Meta:
        model = Role
        fields = ('snowflake', 'name', 'guild', 'color', 'perms', 'order')


class ServerModelMutation(ModelMutation[Server]):
    @classmethod
    def get_instance(cls, req: HttpRequest, server_id: str) -> Server:
        return get_ctx(req).fetch_server(server_id, 'write')


class ServerFormMutation(FormMutationMixin, ServerModelMutation):
    @classmethod
    def mutate(cls, root, info, *, server_id: str, **arguments):
        server = cls.get_instance(info.context, server_id)
        form = cls.get_form(arguments, server)
        form.save()
        return cls(server)


class ServerPrefixMutation(ServerFormMutation):
    class Meta:
        model = Server
        form = forms.ServerPrefixForm

    class Arguments:
        prefix = Argument(String, required=True)

    server = Field(ServerType)


class ServerExtensionsMutation(ServerFormMutation):
    class Meta:
        model = Server
        form = forms.ServerExtensionsForm

    class Arguments:
        extensions = Argument(List(String), required=True)

    server = Field(ServerType)


class ServerModelSyncMutation(ServerFormMutation):
    class Meta:
        model = Server
        form = forms.ServerModelSyncForm

    server = Field(ServerType)


class ServerPermMutation(ServerModelMutation):
    class Meta:
        model = Server

    class Arguments:
        readable = Argument(List(ID), required=True)
        writable = Argument(List(ID), required=True)

    server = Field(ServerType)

    @classmethod
    def mutate(cls, root, info: HasContext, *, server_id: str,
               readable: list[str], writable: list[str]):
        instance = cls.get_instance(info.context, server_id)
        instance.readable = [int(id_) for id_ in readable]
        instance.writable = [int(id_) for id_ in writable]
        instance.save()
        return cls(instance)


class ServerQuery(ObjectType):
    server = Field(ServerType, server_id=ID(required=True))

    @classmethod
    def resolve_server(cls, root, info, server_id) -> Server:
        return get_ctx(info.context).fetch_server(server_id, 'read')


class ServerMutation(ObjectType):
    update_prefix = ServerPrefixMutation.Field()
    update_extensions = ServerExtensionsMutation.Field()
    update_models = ServerModelSyncMutation.Field()
    update_perms = ServerPermMutation.Field()
