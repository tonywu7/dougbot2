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

import re
from typing import Protocol, TypeVar

import discord
from asgiref.sync import sync_to_async
from django.core.exceptions import ValidationError
from django.db import models

from .utils.async_ import async_first, async_get, async_save


class Snowflake(Protocol):
    id: int


T = TypeVar('T', bound=Snowflake)
U = TypeVar('U', bound='Entity')


FORBIDDEN_PREFIXES = re.compile(r'^[*_|~`>]+$')


class NamingMixin:
    """Mixin providing a __str__ and __repr__ for models that have IDs."""

    def discriminator(self, sep='#') -> str:
        """Print the type of this class and its primary key together as a string."""
        return f'{type(self).__name__}{sep}{self.pk}'

    def __str__(self):
        try:
            return self.name
        except Exception:
            return self.discriminator()

    def __repr__(self) -> str:
        return f'<{self.discriminator()} at {hex(id(self))}>'


class Entity(NamingMixin, models.Model):
    """Abstract base class representing a Discord model."""

    class Meta:
        abstract = True

    snowflake: int = models.BigIntegerField(verbose_name='id', primary_key=True, db_index=True)

    @classmethod
    def from_discord(cls: type[U], obj: T, **kwargs) -> U:
        """Create a Django model from a Discord model from discord.py."""
        raise NotImplementedError

    @classmethod
    async def get(cls: type[U], obj: T) -> U:
        return await async_get(cls, snowflake=obj.id)

    @classmethod
    async def first(cls: type[U], obj: T) -> U | None:
        return await async_first(cls.objects.filter(snowflake__exact=obj.id))

    @classmethod
    async def get_or_create(cls: type[U], obj: T, **kwargs) -> tuple[U, bool]:
        """Get the model with a snowflake matching this Discord model,\
        or create it if it doesn't exist"""
        try:
            return (await async_get(cls, snowflake=obj.id, **kwargs), False)
        except cls.DoesNotExist:
            instance = cls.from_discord(obj, **kwargs)
            await async_save(instance)
            return instance, True


def validate_prefix(prefix: str):
    """Validate a string as a command prefix ensuring\
    it doesn't begin with characters that are markdown characters."""

    if FORBIDDEN_PREFIXES.match(prefix):
        raise ValidationError(
            '* _ | ~ ` > are markdown characters. '
            '%(prefix)s as a prefix will cause messages with markdowns '
            'to trigger bot commands.',
            params={'prefix': prefix},
            code='forbidden_chars',
        )


class Server(Entity):
    """Represent a Discord guild.

    Contains most per-guild bot configurations.
    """

    prefix: str = models.CharField(max_length=16, default='d.', validators=[validate_prefix])

    @sync_to_async
    def set_prefix(self, prefix: str):
        validate_prefix(prefix)
        self.prefix = prefix
        self.save()

    @classmethod
    def from_discord(cls, guild: discord.Guild, **kwargs):
        return cls(snowflake=guild.id, perms=guild.default_role.permissions, **kwargs)
