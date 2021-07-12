# serializers.py
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

from __future__ import annotations

from rest_framework.exceptions import ValidationError
from rest_framework.serializers import (CharField, ModelSerializer,
                                        ReadOnlyField)

from ts2.discord.models import (BotCommand, Channel, CommandConstraint, Role,
                                Server)

from .utils.serializer import Int64StringRelatedField


class ChannelSerializer(ModelSerializer):
    id = CharField(source='snowflake')

    class Meta:
        model = Channel
        fields = ['id', 'name', 'type', 'order']


class RoleSerializer(ModelSerializer):
    id = CharField(source='snowflake')

    class Meta:
        model = Role
        fields = ['id', 'name', 'color', 'order']


class ServerDataSerializer(ModelSerializer):
    id = CharField(source='snowflake')
    channels = ChannelSerializer(many=True)
    roles = RoleSerializer(many=True)

    class Meta:
        model = Server
        fields = ['id', 'name', 'channels', 'roles']


class BotCommandSerializer(ModelSerializer):
    name = CharField(source='identifier')
    color = ReadOnlyField(default=0xffffff)

    class Meta:
        model = BotCommand
        fields = ['id', 'name', 'color']


class CommandConstraintSerializer(ModelSerializer):
    class Meta:
        model = CommandConstraint
        fields = ['id', 'name', 'type', 'channels', 'commands', 'roles']

    channels = Int64StringRelatedField(queryset=Channel.objects.all(), many=True, required=False)
    commands = Int64StringRelatedField(queryset=BotCommand.objects.all(), many=True, required=False)
    roles = Int64StringRelatedField(queryset=Role.objects.all(), many=True, required=True)

    def to_internal_value(self, data: dict):
        value = super().to_internal_value(data)
        value['id'] = data.get('id')
        return value

    def create(self, validated_data: dict):
        instance = CommandConstraint()
        instance.collection_id = validated_data['collection_id']
        return self.update(instance, validated_data)

    def update(self, instance: CommandConstraint, validated_data: dict):
        instance.from_dict(validated_data)
        return instance

    def validate_roles(self, roles: list):
        if not roles:
            raise ValidationError(detail='Roles cannot be empty.')
        return roles
