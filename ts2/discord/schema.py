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

from typing import Generic, Protocol, TypeVar

from django.core.exceptions import PermissionDenied
from django.db.models import BigIntegerField, Model
from django.urls import ResolverMatch
from django.utils.datastructures import MultiValueDict
from graphene import (Enum, Field, InputObjectType, List, Mutation, ObjectType,
                      String)
from graphene_django import DjangoObjectType
from graphene_django.converter import (convert_django_field,
                                       convert_field_to_string)
from graphene_django.forms.mutation import DjangoModelFormMutation

from ts2.web.middleware import DiscordContext
from ts2.web.models import User as WebUser

from . import forms, models
from .ext.logging import can_change, get_name

convert_django_field.register(BigIntegerField, convert_field_to_string)

T = TypeVar('T', bound=Model)


class RequestContext(Protocol):
    GET: MultiValueDict
    POST: MultiValueDict
    META: MultiValueDict
    user: WebUser
    resolver_match: ResolverMatch

    def get_ctx() -> DiscordContext:
        ...


class HasContext(Protocol):
    context: RequestContext


class PathScopedDjangoModelMixin(Generic[T]):
    pk_source: str

    class Meta:
        abstract = True

    @classmethod
    def get_manager(cls):
        return cls._meta.model._default_manager

    @classmethod
    def get_instance(cls, info) -> T:
        pk = info.context.resolver_match.kwargs[cls.pk_source]
        instance = cls.get_manager().get(pk=pk)
        return instance

    @classmethod
    def get_form_kwargs(cls, root, info, **input):
        kwargs = {'data': input}
        kwargs['instance'] = cls.get_instance(info)
        return kwargs


class BotCommandType(DjangoObjectType):
    class Meta:
        model = models.BotCommand
        fields = ('id', 'identifier')


class RoleType(DjangoObjectType):
    class Meta:
        model = models.Role
        fields = ('snowflake', 'name', 'guild', 'color', 'perms', 'order')


ChannelTypeEnum = Enum.from_enum(models.ChannelTypeEnum)
ConstraintTypeEnum = Enum.from_enum(models.ConstraintTypeEnum)


class ChannelType(DjangoObjectType):
    type = ChannelTypeEnum(source='type')

    class Meta:
        model = models.Channel
        fields = ('snowflake', 'name', 'guild', 'order')


class CommandConstraintType(DjangoObjectType):
    type = ConstraintTypeEnum(source='type')

    class Meta:
        model = models.CommandConstraint
        fields = ('commands', 'channels', 'type', 'roles', 'name', 'specificity')


class LoggingEntryType(ObjectType):
    key: str = String()
    name: str = String()
    channel: str = String()
    role: str = String()


class ServerType(DjangoObjectType):
    extensions = List(String)
    logging = List(LoggingEntryType)

    class Meta:
        model = models.Server
        fields = (
            'snowflake', 'prefix', 'disabled',
            'name', 'perms',
            'channels', 'roles',
            'command_constraints',
        )

    @staticmethod
    def resolve_logging(obj: models.Server, info: HasContext, **kwargs):
        user = info.context.user
        return [LoggingEntryType(key=k, **v)
                for k, v in obj.logging.items()
                if can_change(user, k)]

    @staticmethod
    def resolve_extensions(obj: models.Server, *args, **kwargs):
        return obj._extensions.split(',')


class StringTemplateType(DjangoObjectType):
    class Meta:
        model = models.StringTemplate
        fields = ('id', 'source', 'server', 'name')


class ServerCreateMutation(DjangoModelFormMutation):
    class Meta:
        form_class = forms.ServerCreateForm
        model_operations = ('create',)


class ServerPrefixMutation(PathScopedDjangoModelMixin[models.Server], DjangoModelFormMutation):
    pk_source = 'guild_id'

    class Meta:
        form_class = forms.ServerPrefixForm
        model_operations = ('update',)


class ServerExtensionsMutation(PathScopedDjangoModelMixin[models.Server], DjangoModelFormMutation):
    pk_source = 'guild_id'

    class Meta:
        form_class = forms.ServerExtensionsForm
        model_operations = ('update',)


class ServerModelSyncMutation(PathScopedDjangoModelMixin, DjangoModelFormMutation):
    pk_source = 'guild_id'

    class Meta:
        form_class = forms.ServerModelSyncForm
        model_operations = ('update',)


class LoggingEntryInput(InputObjectType):
    key: str = String()
    name: str = String()
    channel: str = String()
    role: str = String()


class ServerLoggingMutation(PathScopedDjangoModelMixin[models.Server], Mutation):
    pk_source = 'guild_id'
    server = Field(ServerType)

    class Meta:
        pass

    class Arguments:
        changes = List(LoggingEntryInput)

    @classmethod
    def get_manager(cls):
        return models.Server.objects

    @classmethod
    def mutate(cls, root, info: HasContext, changes: list[LoggingEntryType]):
        user = info.context.user
        instance = cls.get_instance(info)
        logging = instance.logging
        for change in changes:
            key = change.key
            if not can_change(user, key):
                raise PermissionDenied()
            if not change.channel:
                logging.pop(key, None)
                continue
            name = get_name(key)
            logging[change.key] = {
                'name': name,
                'channel': int(change.channel),
                'role': int(change.role),
            }
        instance.save()
        return ServerModelSyncMutation(server=instance)
