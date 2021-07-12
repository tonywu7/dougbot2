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

from rest_framework.serializers import ModelSerializer
from timezone_field.rest_framework import TimeZoneSerializerField

from ts2.discord.models import Role
from ts2.web.utils.serializer import Int64StringRelatedField

from .models import RoleTimezone


class RoleTimezoneSerializer(ModelSerializer):
    timezone = TimeZoneSerializerField(required=True)
    role = Int64StringRelatedField(required=True, queryset=Role.objects.all())

    class Meta:
        model = RoleTimezone
        fields = ['id', 'timezone', 'role']
