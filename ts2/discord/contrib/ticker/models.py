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

from django.db import models

from ts2.discord.models import Channel
from ts2.discord.utils.datetime import utcnow


class TickerChannel(models.Model):
    content: str = models.TextField(blank=False)
    variables: dict = models.JSONField(blank=False, default=dict)

    created: datetime = models.DateTimeField(default=utcnow)
    refresh: float = models.FloatField()
    expire: Optional[datetime] = models.DateTimeField(null=True)

    channel: Channel = models.OneToOneField(Channel, models.CASCADE, primary_key=True, related_name='+')
    parent: Optional[Channel] = models.ForeignKey(Channel, models.CASCADE, related_name='+', null=True)
    placement: dict = models.JSONField(blank=False, default=dict)

    @property
    def expired(self) -> bool:
        return self.expire and datetime.now(timezone.utc) >= self.expire
