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
from django.urls import ResolverMatch
from django.utils.datastructures import MultiValueDict
from graphene import Argument, Enum, Field, List, ObjectType, String
from graphene_django import DjangoObjectType
from graphene_django.converter import (convert_django_field,
                                       convert_field_to_string)

from ts2.web.models import User as WebUser

from . import forms, models
from .apps import DiscordBotConfig
from .models import Server
from .utils.graphql import FormMutationMixin, ModelMutation

convert_django_field.register(BigIntegerField, convert_field_to_string)

ChannelTypeEnum = Enum.from_enum(models.ChannelTypeEnum)


class RequestContext(Protocol):
    GET: MultiValueDict
    POST: MultiValueDict
    META: MultiValueDict
    user: WebUser
    resolver_match: ResolverMatch


class HasContext(Protocol):
    context: RequestContext


class BotType(ObjectType):
    commands = List(String)

    @staticmethod
    def resolve_commands(root, info: HasContext, **kwargs):
        superuser = info.context.user.is_superuser
        instance = DiscordBotConfig.get().bot_thread.get_client()
        if not instance:
            return None
        return [*sorted(
            c.qualified_name for c
            in instance.walk_commands()
            if not instance.is_hidden(c) or superuser
        )]


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
        return obj._extensions.split(',')


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


class ServerPrefixMutation(FormMutationMixin, ModelMutation[Server], model=Server):
    class Arguments:
        prefix = Argument(String, required=True)

    server = Field(ServerType)

    @classmethod
    def mutate(cls, *args, **arguments):
        server = cls.get_instance(arguments)
        form = cls.get_form(forms.ServerPrefixForm, arguments, server)
        form.save()
        return cls(server)


class ServerExtensionsMutation(FormMutationMixin, ModelMutation[Server], model=Server):
    class Arguments:
        extensions = Argument(List(String), required=True)

    server = Field(ServerType)

    @classmethod
    def mutate(cls, *args, **arguments):
        server = cls.get_instance(arguments)
        form = cls.get_form(forms.ServerExtensionsForm, arguments, server)
        form.save()
        return cls(server)


class ServerModelSyncMutation(FormMutationMixin, ModelMutation[Server], model=Server):
    server = Field(ServerType)

    @classmethod
    def mutate(cls, *args, **arguments):
        server = cls.get_instance(arguments)
        form = cls.get_form(forms.ServerModelSyncForm, arguments, server)
        form.save()
        return cls(server)
