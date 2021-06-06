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

from __future__ import annotations

from django.db import models

from discord import Guild


class GuildPreference(models.Model):
    guild_id: int = models.IntegerField()

    prefix: str = models.CharField(max_length=16, default='t;')

    class Meta:
        verbose_name = 'guild preference'
        permissions = [
            ('manage_servers', 'Can invite the bot to servers'),
        ]

    @classmethod
    def prefs_by_guild(cls, guild: Guild) -> GuildPreference:
        return cls.objects.get(guild_id=guild.id)
