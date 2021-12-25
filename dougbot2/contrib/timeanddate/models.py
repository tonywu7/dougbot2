# models.py
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

import pytz
from discord import Role, User
from django.db import models
from timezone_field import TimeZoneField

from dougbot2.models import Entity


class DateTimeSettings(Entity[User]):
    timezone: pytz.BaseTzInfo = TimeZoneField('timezone', blank=True, choices_display='WITH_GMT_OFFSET')
    formatting: str = models.TextField('datetime format', blank=True, default='D MMM YYYY h:mm:ss A')

    @classmethod
    def from_discord(cls, obj: User):
        return cls(snowflake=obj.id)


class RoleTimezone(Entity[Role]):
    timezone: pytz.BaseTzInfo = TimeZoneField('timezone', blank=True, choices_display='WITH_GMT_OFFSET')

    @classmethod
    def from_discord(cls, obj: User):
        return cls(snowflake=obj.id)
