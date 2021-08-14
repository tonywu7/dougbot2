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
from django.utils.functional import classproperty

from ts2.discord.models import Channel
from ts2.discord.utils.fields import NumbersListField, RecordField


class SuggestionChannel(models.Model):
    channel: Channel = models.OneToOneField(Channel, models.CASCADE, primary_key=True, related_name='+')

    title: str = models.TextField()
    description: str = models.TextField(blank=True)

    upvote: str = models.CharField(max_length=512, blank=True, default='🔼')
    downvote: str = models.CharField(max_length=512, blank=True, default='🔽')

    requires_text: bool = models.BooleanField(default=True)
    requires_uploads: int = models.IntegerField(default=0)
    requires_links: int = models.IntegerField(default=0)

    reactions: dict[str, str] = RecordField(default=dict)
    arbiters: list[int] = NumbersListField(default=list)

    @classproperty
    def updatable_fields(cls) -> list[str]:
        return [f.name for f in cls._meta.fields if not f.is_relation]
