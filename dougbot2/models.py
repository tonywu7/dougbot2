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

import logging
import re
from collections.abc import Iterable
from operator import attrgetter, itemgetter
from typing import Generic, Protocol, TypeVar, Union

import discord
from asgiref.sync import sync_to_async
from discord.abc import ChannelType
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import CASCADE, SET_NULL
from django.db.models.query import QuerySet
from duckcord.color import Color2
from duckcord.permissions import Permissions2

from .config import CommandAppConfig
from .utils.async_ import async_first, async_get, async_save
from .utils.fields import ColorField, NumbersListField, PermissionField


class Snowflake(Protocol):
    id: int


T = TypeVar('T', bound=Snowflake)
U = TypeVar('U', bound='Entity')

snowflake_key = itemgetter('snowflake')
snowflake_dot = attrgetter('snowflake')
id_key = itemgetter('id')
id_dot = attrgetter('id')

log = logging.getLogger('discord.models')


def make_channel_type() -> models.IntegerChoices:
    """Derive a Django `IntegerChoices` enum from discord.py's enum of channel types."""
    class ClassDict(dict):
        _member_names = []

    classdict = ClassDict()
    for t in ChannelType:
        classdict[t.name] = t.value
        classdict._member_names.append(t.name)

    return type('ChannelEnum', (models.IntegerChoices,), classdict)


ChannelTypeEnum = make_channel_type()
DiscordChannels = Union[
    discord.CategoryChannel,
    discord.TextChannel,
    discord.VoiceChannel,
    discord.StageChannel,
]
FORBIDDEN_PREFIXES = re.compile(r'^[*_|~`>]+$')


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


class Entity(NamingMixin, models.Model, Generic[T]):
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
        return async_get(cls, snowflake=obj.id)

    @classmethod
    async def first(cls: type[U], obj: T) -> U | None:
        return async_first(cls, snowflake=obj.id)

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


class Server(Entity[discord.Guild]):
    """Represent a Discord guild.

    Contains most per-guild bot configurations.
    """

    _extensions: str = models.TextField(blank=True)

    invited_by = models.ForeignKey('web.User', on_delete=SET_NULL, null=True, related_name='invited_servers')
    disabled: bool = models.BooleanField(default=False)

    channels: QuerySet[Channel]
    roles: QuerySet[Role]

    name: str = models.TextField()
    perms: Permissions2 = PermissionField(verbose_name='default permissions', default=0)

    prefix: str = models.CharField(max_length=16, default='t;', validators=[validate_prefix])

    readable: list[int] = NumbersListField(verbose_name='readable roles', default=list)
    writable: list[int] = NumbersListField(verbose_name='writable roles', default=list)

    @sync_to_async
    def async_set_prefix(self, prefix: str):
        validate_prefix(prefix)
        with transaction.atomic():
            self.prefix = prefix
            self.save()

    @property
    def extensions(self) -> dict[str, CommandAppConfig]:
        """Return all bot cogs this server has enabled."""
        if not self._extensions:
            return {}
        exts = self._extensions.split(',')
        configs = {}
        for label in exts:
            try:
                configs[label] = apps.get_app_config(label)
            except LookupError:
                log.warning(f'No such extension {label}')
        return configs

    @extensions.setter
    def extensions(self, configs: Iterable[str | CommandAppConfig]):
        self._extensions = ','.join([conf.label if isinstance(conf, CommandAppConfig) else conf
                                     for conf in configs])

    @classmethod
    def from_discord(cls, guild: discord.Guild, **kwargs):
        return cls(snowflake=guild.id, perms=guild.default_role.permissions, **kwargs)


class Channel(Entity[DiscordChannels]):
    name: str = models.CharField(max_length=120)
    type: int = models.IntegerField(choices=ChannelTypeEnum.choices)
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='channels')
    order: int = models.IntegerField(default=0)
    category: Channel = models.ForeignKey('self', on_delete=SET_NULL, null=True)

    @classmethod
    def from_discord(cls, channel: DiscordChannels, **kwargs) -> Channel:
        return cls(
            snowflake=channel.id,
            name=channel.name,
            guild_id=channel.guild.id,
            type=channel.type.value,
            category_id=channel.category_id,
            **kwargs,
        )


class Role(Entity[discord.Role]):
    name: str = models.CharField(max_length=120)
    color: Color2 = ColorField()
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='roles')
    perms: Permissions2 = PermissionField(verbose_name='permissions')
    order: int = models.IntegerField(default=0)

    @classmethod
    def from_discord(cls, role: discord.Role) -> Role:
        return cls(
            snowflake=role.id,
            name=role.name,
            color=role.color,
            guild_id=role.guild.id,
            perms=role.permissions,
        )


class User(Entity[discord.User]):
    name: str = models.CharField(max_length=120, verbose_name='username')
    discriminator: int = models.IntegerField()

    @classmethod
    def from_discord(cls, user: discord.User):
        return cls(
            snowflake=user.id,
            name=user.name,
            discriminator=user.discriminator,
        )


class Member(Entity[discord.Member]):
    nickname: str = models.CharField(max_length=64, blank=True)
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='members')
    profile: User = models.ForeignKey(User, on_delete=CASCADE, related_name='memberships')

    @classmethod
    def from_discord(cls, member: discord.Member) -> Member:
        return cls(
            snowflake=member.id,
            guild_id=member.guild.id,
            nickname=member.nick,
            profile_id=member.id,
        )
