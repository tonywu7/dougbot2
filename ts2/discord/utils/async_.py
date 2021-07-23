# async_.py
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

from typing import Optional, TypeVar

from asgiref.sync import sync_to_async
from django.db.models import Model, QuerySet

M = TypeVar('M', bound=Model)


@sync_to_async
def async_get(q: QuerySet[M], **kwargs) -> M:
    return q.get(**kwargs)


@sync_to_async
def async_list(q: QuerySet[M]) -> list[M]:
    return [*q.all()]


@sync_to_async
def async_first(q: QuerySet[M]) -> Optional[M]:
    return q.first()


@sync_to_async
def async_save(item: M, *args, **kwargs) -> M:
    item.save(*args, **kwargs)
    return item


async_get.__annotations__ = {'q': QuerySet[M], 'return': M}
async_list.__annotations__ = {'q': QuerySet[M], 'return': list[M]}
async_first.__annotations__ = {'q': QuerySet[M], 'return': Optional[M]}
