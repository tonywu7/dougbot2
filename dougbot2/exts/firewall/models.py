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

from ...utils.fields import NumbersListField


class Blacklisted(models.Model):
    """Represent a Discord entity that is barred from interacting with the bot."""

    class Meta:
        verbose_name = "blacklisted entity"
        verbose_name_plural = "blacklisted entities"

    snowflake: int = models.BigIntegerField(
        verbose_name="id", primary_key=True, db_index=True
    )


class AccessRule(models.Model):
    command: str = models.TextField()
    channel_id: int = models.BigIntegerField()
    roles: list[int] = NumbersListField()
    enabled: bool = models.BooleanField()
    priority: int = models.IntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=("command", "channel_id"))]
