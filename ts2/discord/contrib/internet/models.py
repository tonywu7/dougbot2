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
from django.db import models
from django.db.models import CASCADE
from timezone_field import TimeZoneField

from ts2.discord.models import Role


class RoleTimezone(models.Model):
    timezone: pytz.BaseTzInfo = TimeZoneField('timezone', blank=True, choices_display='WITH_GMT_OFFSET')
    role: Role = models.OneToOneField(Role, on_delete=CASCADE, related_name='+')
