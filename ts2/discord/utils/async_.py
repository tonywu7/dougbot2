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

from typing import Optional, TypeVar, Union

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import Model, QuerySet

M = TypeVar('M', bound=Model)


@sync_to_async
def async_get(q: Union[type[M], QuerySet[M]], **kwargs) -> M:
    if isinstance(q, type) and issubclass(q, Model):
        q = q.objects
    return q.get(**kwargs)


@sync_to_async
def async_list(q: QuerySet[M]) -> list[M]:
    return [*q.all()]


@sync_to_async
def async_first(q: QuerySet[M]) -> Optional[M]:
    return q.first()


@sync_to_async
def async_exists(q: QuerySet[M]) -> bool:
    return q.exists()


@sync_to_async
def async_save(item: M, *args, **kwargs) -> M:
    item.save(*args, **kwargs)
    return item


@sync_to_async
def async_delete(item: M):
    return item.delete()


@sync_to_async
def async_get_or_create(m: type[M], defaults=None, **kwargs) -> tuple[M, bool]:
    return m.objects.get_or_create(defaults, **kwargs)


class async_atomic:
    """An async version of the `django.db.transaction.atomic` context manager.

    Usage: `async with async_atomic(): ...`
    """

    def __init__(self, savepoint=True, durable=False):
        self.kwargs = {'savepoint': savepoint,
                       'durable': durable}

    @sync_to_async
    def __aenter__(self):
        transaction.atomic(**self.kwargs).__enter__()

    @sync_to_async
    def __aexit__(self, exc_type, exc, tb):
        transaction.atomic().__exit__(exc_type, exc, tb)


class Promise:
    # TODO: remove
    @classmethod
    async def resolve(cls, *args, **kwargs):
        return args, kwargs

    @classmethod
    async def reject(cls, exc: Exception):
        raise exc
