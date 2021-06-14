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
from typing import Dict, Generic, Iterable, List, TypeVar, Union

import discord
import inflect
from discord.abc import ChannelType
from django.apps import apps
from django.db import models
from django.db.models import CASCADE
from django.db.models.query import QuerySet

from telescope2.web.config import CommandAppConfig

inflection = inflect.engine()

T = TypeVar(
    'T', discord.User, discord.Guild, discord.Member, discord.Role,
    discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel,
)
U = TypeVar('U', bound='Entity')


def convert_channel_type() -> models.IntegerChoices:
    class ClassDict(dict):
        _member_names = []

    classdict = ClassDict()
    for t in ChannelType:
        classdict[t.name] = t.value
        classdict._member_names.append(t.name)

    return type('ChannelKind', (models.IntegerChoices,), classdict)


ChannelKind = convert_channel_type()
DiscordChannels = Union[
    discord.CategoryChannel,
    discord.TextChannel,
    discord.VoiceChannel,
    discord.StageChannel,
]


class SubclassMetaMixin:
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        try:
            if cls.Meta is super().Meta:
                __dict__ = {}
            else:
                __dict__ = cls.Meta.__dict__
        except AttributeError:
            __dict__ = {}
        else:
            __dict__ = {k: v for k, v in __dict__.items() if k[0] != '_' and k != 'abstract'}
        cls.Meta = type('Meta', (object,), __dict__)


class NamingMixin:
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls.Meta, 'verbose_name'):
            cls.Meta.verbose_name = cls.__name__.lower()
        if not hasattr(cls.Meta, 'verbose_name_plural'):
            cls.Meta.verbose_name_plural = inflection.plural(cls.Meta.verbose_name)

    def discriminator(self, sep='#') -> str:
        return f'{type(self).__name__}{sep}{self.pk}'

    def __str__(self):
        return self.discriminator()

    def __repr__(self) -> str:
        return f'<{self.discriminator()} at {hex(id(self))}>'


class PermissionField(models.IntegerField):
    def to_python(self, value) -> discord.Permissions | None:
        number = super().to_python(value)
        if number is None:
            return None
        return discord.Permissions(number)

    def get_prep_value(self, value: discord.Permissions | None):
        return super().get_prep_value(value and value.value)


class ColorField(models.IntegerField):
    def to_python(self, value) -> discord.Color | None:
        number = super().to_python(value)
        if number is None:
            return None
        return discord.Color(number)

    def get_prep_value(self, value: discord.Color):
        return super().get_prep_value(value and value.value)


class ModelTranslator(Generic[T, U]):
    @classmethod
    def from_discord(cls, discord_model: T) -> U:
        raise NotImplementedError

    @classmethod
    def updatable_fields(cls) -> List[str]:
        raise NotImplementedError


class Entity(NamingMixin, SubclassMetaMixin, models.Model):
    snowflake: int = models.BigIntegerField(verbose_name='id', primary_key=True, db_index=True)

    class Meta:
        abstract = True


class User(Entity, ModelTranslator[discord.User, 'User']):
    name: str = models.CharField(max_length=120, verbose_name='username')
    discriminator: int = models.IntegerField()

    @classmethod
    def from_discord(cls, user: discord.User):
        return cls(
            snowflake=user.id,
            name=user.name,
            discriminator=user.discriminator,
        )

    @classmethod
    def updatable_fields(cls) -> List[str]:
        return ['name', 'discriminator']


class Server(Entity, ModelTranslator[discord.Guild, 'Server']):
    FORBIDDEN_PREFIXES = re.compile(r'^[*_|~`>]+$')

    prefix: str = models.CharField(max_length=16, default='t;')
    _extensions: str = models.TextField(blank=True)

    channels: QuerySet[Channel]
    roles: QuerySet[Role]
    members: QuerySet[Member]

    perms: discord.Permissions = PermissionField(verbose_name='default permissions', default=0)

    @property
    def extensions(self) -> Dict[str, CommandAppConfig]:
        if not self._extensions:
            return {}
        exts = self._extensions.split(',')
        return {label: apps.get_app_config(label) for label in exts}

    @extensions.setter
    def extensions(self, configs: Iterable[str | CommandAppConfig]):
        self._extensions = ','.join([conf.label if isinstance(conf, CommandAppConfig) else conf
                                     for conf in configs])

    @classmethod
    def validate_prefix(cls, prefix: str):
        if cls.FORBIDDEN_PREFIXES.match(prefix):
            raise ValueError(
                '* _ | ~ ` > are markdown characters. '
                '%(prefix)s as a prefix will cause messages with markdowns '
                'to trigger bot commands.' % {'prefix': prefix},
            )

    @classmethod
    def from_discord(cls, guild: discord.Guild):
        return cls(
            snowflake=guild.id,
            perms=guild.default_role.permissions,
        )

    @classmethod
    def updatable_fields(cls) -> List[str]:
        return ['perms']


class Channel(Entity, ModelTranslator[DiscordChannels, 'Channel']):
    name: str = models.CharField(max_length=120)
    type: int = models.IntegerField(choices=ChannelKind.choices)
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='channels')
    order: int = models.IntegerField(default=0)

    @classmethod
    def from_discord(cls, channel: DiscordChannels) -> Channel:
        return cls(
            snowflake=channel.id,
            name=channel.name,
            guild_id=channel.guild.id,
            type=channel.type.value,
        )

    @classmethod
    def updatable_fields(cls) -> List[str]:
        return ['name', 'type']



class Member(Entity, ModelTranslator[discord.Member, 'Member']):
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

    @classmethod
    def updatable_fields(cls) -> List[str]:
        return ['nickname']


class Role(Entity, ModelTranslator[discord.Role, 'Role']):
    name: str = models.CharField(max_length=120)
    color: int = ColorField()
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='roles')
    perms: discord.Permissions = PermissionField(verbose_name='permissions')
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
    def updatable_fields(cls) -> List[str]:
        return ['name', 'color', 'perms']


class BotCommand(models.Model):
    identifier: str = models.CharField(max_length=120, unique=True)
