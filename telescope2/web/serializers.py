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

from rest_framework.serializers import ModelSerializer

from telescope2.discord import models


class ChannelSerializer(ModelSerializer):
    class Meta:
        model = models.Channel
        fields = ['snowflake', 'name', 'type', 'order']


class RoleSerializer(ModelSerializer):
    class Meta:
        model = models.Role
        fields = ['snowflake', 'name', 'color', 'order']


class BotCommandSerializer(ModelSerializer):
    class Meta:
        model = models.BotCommand
        fields = ['identifier']


class CommandConstraintSerializer(ModelSerializer):
    class Meta:
        model = models.CommandConstraint
        fields = ['id', 'guild', 'name', 'type', 'channels', 'commands', 'roles']
