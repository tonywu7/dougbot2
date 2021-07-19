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

from django.db.models import BigIntegerField
from django.http import HttpRequest
from graphene import Argument, Enum, Field, List, ObjectType, String
from graphene_django import DjangoObjectType
from graphene_django.converter import (convert_django_field,
                                       convert_field_to_string)

from ts2.web.middleware import get_server

from . import forms, models
from .apps import get_commands
from .models import Server
from .utils.graphql import FormMutationMixin, ModelMutation

convert_django_field.register(BigIntegerField, convert_field_to_string)

ChannelTypeEnum = Enum.from_enum(models.ChannelTypeEnum)


class HasContext(Protocol):
    context: HttpRequest


class BotType(ObjectType):
    commands = List(String)

    @staticmethod
    def resolve_commands(root, info: HasContext, **kwargs):
        return get_commands(info.context)


class ServerType(DjangoObjectType):
    extensions = List(String)

    class Meta:
        model = Server
        fields = (
            'snowflake', 'prefix', 'disabled',
            'name', 'perms',
            'channels', 'roles',
        )

    @staticmethod
    def resolve_extensions(obj: Server, *args, **kwargs):
        return obj.extensions


class ChannelType(DjangoObjectType):
    type = ChannelTypeEnum(source='type')

    class Meta:
        model = models.Channel
        fields = ('snowflake', 'name', 'guild', 'order')


class RoleType(DjangoObjectType):
    class Meta:
        model = models.Role
        fields = ('snowflake', 'name', 'guild', 'color', 'perms', 'order')


class StringTemplateType(DjangoObjectType):
    class Meta:
        model = models.StringTemplate
        fields = ('id', 'source', 'server', 'name')


class ServerMutation(ModelMutation[Server]):
    @classmethod
    def get_instance(cls, req: HttpRequest, server_id: str) -> Server:
        return get_server(req, server_id)


class ServerFormMutation(FormMutationMixin, ServerMutation):
    @classmethod
    def mutate(cls, info, *, item_id: str, **arguments):
        server = cls.get_instance(info, item_id)
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
