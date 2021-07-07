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

from django.db import models
from django.db.models import CASCADE

from telescope2.discord.models import Role, User


class Timezone(models.Model):
    tz: str = models.CharField(max_length=128)

    class Meta:
        abstract = True


class UserTimezone(Timezone):
    user: User = models.ForeignKey(User, on_delete=CASCADE, related_name='+')


class RoleTimezone(Timezone):
    role: Role = models.ForeignKey(Role, on_delete=CASCADE, related_name='+')
