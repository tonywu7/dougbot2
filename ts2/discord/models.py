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
import inflect
from discord.abc import ChannelType
from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CASCADE, SET_NULL
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet
from duckcord.color import Color2
from duckcord.permissions import Permissions2

from .config import CommandAppConfig
from .utils.fields import ColorField, NumbersListField, PermissionField

inflection = inflect.engine()

T = TypeVar(
    'T', discord.User, discord.Guild, discord.Member, discord.Role,
    discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel,
)
U = TypeVar('U', bound='Entity')

snowflake_key = itemgetter('snowflake')
snowflake_dot = attrgetter('snowflake')
id_key = itemgetter('id')
id_dot = attrgetter('id')

log = logging.getLogger('discord.models')


def make_channel_type() -> models.IntegerChoices:
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
    if FORBIDDEN_PREFIXES.match(prefix):
        raise ValidationError(
            '* _ | ~ ` > are markdown characters. '
            '%(prefix)s as a prefix will cause messages with markdowns '
            'to trigger bot commands.',
            params={'prefix': prefix},
            code='forbidden_chars',
        )


class NamingMixin:
    def discriminator(self, sep='#') -> str:
        return f'{type(self).__name__}{sep}{self.pk}'

    def __str__(self):
        try:
            return self.name
        except Exception:
            return self.discriminator()

    def __repr__(self) -> str:
        return f'<{self.discriminator()} at {hex(id(self))}>'


class ModelTranslator(Generic[T, U]):
    @classmethod
    def from_discord(cls, discord_model: T) -> U:
        raise NotImplementedError

    @classmethod
    def updatable_fields(cls) -> list[str]:
        raise NotImplementedError


class ORMAccess(Protocol):
    objects: BaseManager


class ServerScoped(ORMAccess):
    guild: Server


class Entity(NamingMixin, models.Model):
    snowflake: int = models.BigIntegerField(verbose_name='id', primary_key=True, db_index=True)

    class Meta:
        abstract = True


class Server(Entity, ModelTranslator[discord.Guild, 'Server']):
    _extensions: str = models.TextField(blank=True)

    invited_by = models.ForeignKey('web.User', on_delete=SET_NULL, null=True, related_name='invited_servers')
    disabled: bool = models.BooleanField(default=False)

    channels: QuerySet[Channel]
    roles: QuerySet[Role]

    name: str = models.TextField()
    perms: Permissions2 = PermissionField(verbose_name='default permissions', default=0)

    prefix: str = models.CharField(max_length=16, default='t;', validators=[validate_prefix])
    logging: dict = models.JSONField(verbose_name='logging config', default=dict)

    readable: list[int] = NumbersListField(verbose_name='readable roles', default=list)
    writable: list[int] = NumbersListField(verbose_name='writable roles', default=list)

    @property
    def extensions(self) -> dict[str, CommandAppConfig]:
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
    def from_discord(cls, guild: discord.Guild):
        return cls(
            snowflake=guild.id,
            perms=guild.default_role.permissions,
        )

    @classmethod
    def updatable_fields(cls) -> list[str]:
        return ['perms']


class Channel(Entity, ModelTranslator[DiscordChannels, 'Channel']):
    name: str = models.CharField(max_length=120)
    type: int = models.IntegerField(choices=ChannelTypeEnum.choices)
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='channels')
    order: int = models.IntegerField(default=0)
    category: Channel = models.ForeignKey('self', on_delete=SET_NULL, null=True)

    @classmethod
    def from_discord(cls, channel: DiscordChannels) -> Channel:
        instance = cls(
            snowflake=channel.id,
            name=channel.name,
            guild_id=channel.guild.id,
            type=channel.type.value,
            category_id=channel.category_id,
        )
        return instance

    @classmethod
    def updatable_fields(cls) -> list[str]:
        return ['name', 'type', 'category_id']


class Role(Entity, ModelTranslator[discord.Role, 'Role']):
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

    @classmethod
    def updatable_fields(cls) -> list[str]:
        return ['name', 'color', 'perms']


class Blacklisted(Entity):
    class Meta:
        verbose_name = 'blacklisted entity'
        verbose_name_plural = 'blacklisted entities'
