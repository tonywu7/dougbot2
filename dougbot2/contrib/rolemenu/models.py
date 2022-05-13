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


class RoleStatistics(models.Model):
    channel_id: int = models.BigIntegerField()
    message_id: int = models.BigIntegerField()

    title: str = models.TextField()
    description: str = models.TextField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["channel_id", "message_id"], name="msg_id"),
        ]


class RoleCounter(models.Model):
    menu: RoleStatistics = models.ForeignKey(
        RoleStatistics, on_delete=models.CASCADE, related_name="roles"
    )

    guild_id: int = models.BigIntegerField()

    role_id: int = models.BigIntegerField()
    emote: str = models.CharField(max_length=256)
    description: str = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["role_id"]), models.Index(fields=["guild_id"])]
