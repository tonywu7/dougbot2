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

from django.db.models import BigIntegerField, Model
from django.urls import ResolverMatch
from django.utils.datastructures import MultiValueDict
from graphene import Enum, Field, List, String
from graphene_django import DjangoObjectType
from graphene_django.converter import (convert_django_field,
                                       convert_field_to_string)
from graphene_django.forms.mutation import DjangoModelFormMutation

from ts2.web.middleware import DiscordContext
from ts2.web.models import User as WebUser

from . import forms, models
from .ext.acl.schema import (AccessControlType, ACLDeleteMutation,
                             ACLUpdateMutation)
from .ext.logging import LoggingEntryType, LoggingMutation, can_change

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


class RoleType(DjangoObjectType):
    class Meta:
        model = models.Role
        fields = ('snowflake', 'name', 'guild', 'color', 'perms', 'order')


ChannelTypeEnum = Enum.from_enum(models.ChannelTypeEnum)


class ChannelType(DjangoObjectType):
    type = ChannelTypeEnum(source='type')

    class Meta:
        model = models.Channel
        fields = ('snowflake', 'name', 'guild', 'order')


class ServerType(DjangoObjectType):
    extensions = List(String)
    logging = List(LoggingEntryType)
    acl = List(AccessControlType)

    class Meta:
        model = models.Server
        fields = (
            'snowflake', 'prefix', 'disabled',
            'name', 'perms',
            'channels', 'roles',
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

    @staticmethod
    def resolve_acl(obj: models.Server, *args, **kwargs):
        return AccessControlType.serialize([*obj.acl.all()])


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


class ServerLoggingMutation(PathScopedDjangoModelMixin[models.Server], LoggingMutation):
    pk_source = 'guild_id'
    server = Field(ServerType)

    class Meta:
        pass

    @classmethod
    def get_manager(cls):
        return models.Server.objects

    @classmethod
    def mutate(cls, root, info: HasContext, input):
        user = info.context.user
        instance = cls.get_instance(info)
        logging = instance.logging
        cls.validate_permission(user, input)
        instance.logging = cls.apply(logging, input)
        instance.save()
        return ServerModelSyncMutation(server=instance)


class ServerACLDeleteMutation(PathScopedDjangoModelMixin[models.Server], ACLDeleteMutation):
    pk_source = 'guild_id'

    class Meta:
        pass

    @classmethod
    def get_manager(cls):
        return models.Server.objects

    @classmethod
    def get_queryset(cls, info):
        return cls.get_server(info).acl.all()

    @classmethod
    def get_server(cls, info):
        return cls.get_instance(info)


class ServerACLUpdateMutation(PathScopedDjangoModelMixin[models.Server], ACLUpdateMutation):
    pk_source = 'guild_id'
    acl = List(AccessControlType)

    class Meta:
        pass

    @classmethod
    def get_manager(cls):
        return models.Server.objects

    @classmethod
    def get_server(cls, info):
        return cls.get_instance(info)

    @classmethod
    def get_queryset(cls, info):
        return cls.get_server(info).acl.all()

    @classmethod
    def mutate(cls, root, info: HasContext, input):
        cls.delete(info, input)
        instances = cls.create(info, input)
        acl = AccessControlType.serialize(instances)
        return cls(acl=acl)
