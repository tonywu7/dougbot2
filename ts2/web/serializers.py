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

from rest_framework.serializers import CharField, ModelSerializer

from ts2.discord.models import Channel, Role, Server


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
