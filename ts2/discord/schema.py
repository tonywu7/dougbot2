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

from django.db import models
from graphene import Enum
from graphene_django import DjangoObjectType
from graphene_django.converter import (convert_django_field,
                                       convert_field_to_string)

from .models import (BotCommand, Channel, ChannelTypeEnum, CommandConstraint,
                     ConstraintTypeEnum, Role, Server, StringTemplate)

convert_django_field.register(models.BigIntegerField, convert_field_to_string)


class BotCommandType(DjangoObjectType):
    class Meta:
        model = BotCommand
        fields = ('id', 'identifier')


class RoleType(DjangoObjectType):
    class Meta:
        model = Role
        fields = ('snowflake', 'name', 'guild', 'color', 'perms', 'order')


ChannelTypeEnum = Enum.from_enum(ChannelTypeEnum)
ConstraintTypeEnum = Enum.from_enum(ConstraintTypeEnum)


class ChannelType(DjangoObjectType):
    type = ChannelTypeEnum(source='type')

    class Meta:
        model = Channel
        fields = ('snowflake', 'name', 'guild', 'order')


class CommandConstraintType(DjangoObjectType):
    type = ConstraintTypeEnum(source='type')

    class Meta:
        model = CommandConstraint
        fields = ('commands', 'channels', 'type', 'roles', 'name', 'specificity')


class ServerType(DjangoObjectType):
    class Meta:
        model = Server
        fields = (
            'snowflake', 'prefix', 'disabled',
            'name', 'perms', 'logging',
            'channels', 'roles',
            'command_constraints',
        )


class StringTemplateType(DjangoObjectType):
    class Meta:
        model = StringTemplate
        fields = ('id', 'source', 'server', 'name')
