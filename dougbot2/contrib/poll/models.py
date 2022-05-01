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

import re

from discord import TextChannel
from django.db import models

from dougbot2.models import Entity
from dougbot2.utils.fields import NumbersListField, RecordField

RE_UNICODE_VARIATIONS = re.compile('[\ufe00-\ufe0f]')


class SuggestionChannel(Entity):
    title: str = models.TextField(default='Suggestion')
    description: str = models.TextField(blank=True)

    upvote: str = models.CharField(max_length=512, blank=True, default='🔼')
    downvote: str = models.CharField(max_length=512, blank=True, default='🔽')

    requires_text: bool = models.BooleanField(default=True)
    requires_uploads: int = models.IntegerField(default=0)
    requires_links: int = models.IntegerField(default=0)

    reactions: dict[str, str] = RecordField(default=dict)
    arbiters: list[int] = NumbersListField(default=list)

    voting_history: bool = models.BooleanField(null=False, default=True)

    @classmethod
    def from_discord(cls, obj: TextChannel, **kwargs):
        return cls(snowflake=obj)

    @property
    def all_emotes(self) -> dict[str, str]:
        emotes = {self.upvote: '', self.downvote: '', **self.reactions}
        return {
            RE_UNICODE_VARIATIONS.sub('', k): v
            for k, v in emotes.items() if k
        }
