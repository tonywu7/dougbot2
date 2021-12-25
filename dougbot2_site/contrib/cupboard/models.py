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

from pathlib import Path
from django.db import models
from django.utils import timezone

from ts2.discord.models import Server


class ServerResource(models.Model):
    @staticmethod
    def server_prefixed_path(guild_id: int, filename: str) -> str:
        return Path('guild') / str(guild_id) / 'uploads' / filename

    def upload_path(self, filename: str) -> str:
        now = timezone.now()
        path = f'{now.year:04d}/{now.month:02d}/{now.day:02d}/{filename}'
        return self.server_prefixed_path(self.server.snowflake, path)

    server: Server = models.ForeignKey(Server, on_delete=models.CASCADE)
    upload: models.FieldFile = models.FileField(upload_to=upload_path)
