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

from datetime import datetime, timezone
from typing import Optional

import arrow
from django.db import models


class TickerChannel(models.Model):
    channel_id: int = models.BigIntegerField()

    content: str = models.TextField(blank=False)
    variables: dict = models.JSONField(blank=False, default=dict)

    created: datetime = models.DateTimeField(default=arrow.utcnow)
    refresh: float = models.FloatField()
    expire: Optional[datetime] = models.DateTimeField(null=True)

    parent_id: Optional[int] = models.BigIntegerField()
    placement: dict = models.JSONField(blank=False, default=dict)

    @property
    def expired(self) -> bool:
        return self.expire and datetime.now(timezone.utc) >= self.expire
