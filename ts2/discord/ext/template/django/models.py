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
from django.db.models import CASCADE

from ....models import Server


class BaseTemplate(models.Model):
    class Meta:
        abstract = True

    source: str = models.TextField(blank=True)

    def __str__(self) -> str:
        meta = self._meta
        return f'{meta.app_label}/{meta.model_name}/{self.id}.html'


class StringTemplate(BaseTemplate):
    server: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='templates')
    name: str = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['server_id', 'name'],
                name='uq_%(app_label)s_%(class)s_server_id_name',
            ),
        ]
