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

from typing import Dict, List

from more_itertools import partition
from rest_framework.exceptions import ValidationError
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.serializers import CharField, ModelSerializer, ReadOnlyField

from telescope2.discord.models import (BotCommand, Channel, CommandConstraint,
                                       CommandConstraintList, Role, Server)


class Int64StringRelatedField(PrimaryKeyRelatedField):
    def to_representation(self, value):
        return str(super().to_representation(value))


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

    def to_internal_value(self, data: Dict):
        value = super().to_internal_value(data)
        value['id'] = data.get('id')
        return value

    def create(self, validated_data: Dict):
        instance = CommandConstraint()
        instance.collection_id = validated_data['collection_id']
        return self.update(instance, validated_data)

    def update(self, instance: CommandConstraint, validated_data: Dict):
        instance.from_dict(validated_data)
        return instance

    def validate_roles(self, roles: List):
        if not roles:
            raise ValidationError(detail='Roles cannot be empty.')
        return roles


class CommandConstraintListSerializer(ModelSerializer):
    guild = Int64StringRelatedField(queryset=Server.objects.all())
    constraints = CommandConstraintSerializer(many=True)

    class Meta:
        model = CommandConstraintList
        fields = ['guild', 'constraints']

    def create(self, validated_data: Dict[str, str]):
        cc_list = CommandConstraintList(guild=validated_data['guild'])
        cc_list.save()
        return cc_list

    def update(self, instance: CommandConstraintList, validated_data: Dict):
        serializer = CommandConstraintSerializer()

        cc_list: List[Dict] = validated_data['constraints']
        to_create, to_update = partition(lambda c: c.get('id'), cc_list)

        to_create = [{**d, 'collection_id': instance.guild_id} for d in to_create]
        for cc in to_create:
            serializer.create(cc)

        for item in to_update:
            serializer.update(instance.constraints.get(pk=item['id']), item)

        return instance
