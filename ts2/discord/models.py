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
from datetime import datetime
from operator import attrgetter, itemgetter
from typing import Generic, Protocol, TypeVar, Union

import discord
import inflect
import pytz
from asgiref.sync import sync_to_async
from discord.abc import ChannelType
from django.apps import apps
from django.conf.locale import LANG_INFO
from django.db import models
from django.db.models import CASCADE, SET_NULL
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet
from timezone_field import TimeZoneField

from ts2.web.config import CommandAppConfig
from ts2.web.models import User as SystemUser

from .utils.markdown import strong, tag_literal

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


def make_locale_type() -> models.TextChoices:
    class ClassDict(dict):
        _member_names = []

    classdict = ClassDict()
    for k, v in LANG_INFO.items():
        name = v.get('name')
        if not name:
            continue
        attr = k.replace('-', '_')
        classdict[attr] = (k, name)
        classdict._member_names.append(attr)

    return type('LocaleType', (models.TextChoices,), classdict)


ChannelTypeEnum = make_channel_type()
LocaleType = make_locale_type()
DiscordChannels = Union[
    discord.CategoryChannel,
    discord.TextChannel,
    discord.VoiceChannel,
    discord.StageChannel,
]


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


class PermissionField(models.BigIntegerField):
    def to_python(self, value) -> discord.Permissions | None:
        number = super().to_python(value)
        if number is None:
            return None
        return discord.Permissions(number)

    def get_prep_value(self, value: discord.Permissions | None):
        if isinstance(value, discord.Permissions):
            return super().get_prep_value(value.value)
        return super().get_prep_value(value)


class ColorField(models.IntegerField):
    def to_python(self, value) -> discord.Color | None:
        number = super().to_python(value)
        if number is None:
            return None
        return discord.Color(number)

    def get_prep_value(self, value: discord.Color):
        if isinstance(value, discord.Color):
            return super().get_prep_value(value.value)
        return super().get_prep_value(value)



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


class User(Entity, ModelTranslator[discord.User, 'User']):
    name: str = models.CharField(max_length=120, verbose_name='username')
    discriminator: int = models.IntegerField()

    timezone: pytz.BaseTzInfo = TimeZoneField('timezone', blank=True, choices_display='WITH_GMT_OFFSET')
    datetimefmt: str = models.TextField('datetime format', blank=True)
    locale: str = models.CharField('language', max_length=120, blank=True, choices=LocaleType.choices)

    _default: bool = False

    @classmethod
    def from_discord(cls, user: discord.User):
        return cls(
            snowflake=user.id,
            name=user.name,
            discriminator=user.discriminator,
        )

    @classmethod
    def updatable_fields(cls) -> list[str]:
        return ['name', 'discriminator']

    @classmethod
    def defaultuser(cls, **kwargs):
        instance = cls(datetimefmt='%d %b %Y %l:%M:%S %p', locale='en', **kwargs)
        instance._default = True
        return instance

    @classmethod
    @sync_to_async
    def aget(cls, user: discord.User) -> User:
        try:
            return cls.objects.get(snowflake=user.id)
        except cls.DoesNotExist:
            return cls.defaultuser(snowflake=user.id, name=user.name,
                                   discriminator=user.discriminator)

    @sync_to_async
    def asave(self, *args, **kwargs):
        return self.save(*args, **kwargs)

    @sync_to_async
    def save_timezone(self, tz: pytz.BaseTzInfo | str):
        self.timezone = tz
        self.save()

    @property
    def isdefault(self):
        return self._default

    def format_prefs(self) -> dict[str, str]:
        info = {}
        for field_name in ('timezone', 'datetimefmt', 'locale'):
            field = self._meta.get_field(field_name)
            val = getattr(self, field_name)
            if field.choices:
                val = dict(field.choices).get(val)
            info[field.verbose_name] = val
        return info

    def format_datetime(self, dt: datetime):
        return dt.strftime(self.datetimefmt)


class Server(Entity, ModelTranslator[discord.Guild, 'Server']):
    FORBIDDEN_PREFIXES = re.compile(r'^[*_|~`>]+$')

    invited_by: SystemUser = models.ForeignKey(SystemUser, on_delete=SET_NULL, null=True, related_name='invited_servers')
    disabled: bool = models.BooleanField(default=False)

    prefix: str = models.CharField(max_length=16, default='t;')
    _extensions: str = models.TextField(blank=True)

    channels: QuerySet[Channel]
    roles: QuerySet[Role]
    members: QuerySet[Member]

    name: str = models.TextField()
    perms: discord.Permissions = PermissionField(verbose_name='default permissions', default=0)

    logging: dict = models.JSONField(verbose_name='logging config', default=dict)

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
    def updatable_fields(cls) -> list[str]:
        return ['perms']


class Channel(Entity, ModelTranslator[DiscordChannels, 'Channel']):
    name: str = models.CharField(max_length=120)
    type: int = models.IntegerField(choices=ChannelTypeEnum.choices)
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
    def updatable_fields(cls) -> list[str]:
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
    def updatable_fields(cls) -> list[str]:
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
    def updatable_fields(cls) -> list[str]:
        return ['name', 'color', 'perms']


class BotCommand(NamingMixin, models.Model):
    identifier: str = models.CharField(max_length=120, unique=True)

    class Meta:
        verbose_name = 'bot command'

    def __str__(self) -> str:
        return self.identifier


class ConstraintTypeEnum(models.IntegerChoices):
    NONE = 0
    ANY = 1
    ALL = 2


class CommandConstraint(NamingMixin, models.Model):
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='command_constraints')
    commands: QuerySet[BotCommand] = models.ManyToManyField(BotCommand, related_name='constraints')
    channels: QuerySet[Channel] = models.ManyToManyField(Channel, related_name='+')
    roles: QuerySet[Role] = models.ManyToManyField(Role, related_name='+')

    name: str = models.TextField(blank=False)
    type: int = models.IntegerField(choices=ConstraintTypeEnum.choices)
    specificity: int = models.IntegerField(default=0)
    error_msg: str = models.TextField(blank=True, verbose_name='error message')

    @classmethod
    def calc_specificity(cls, constraint_type: int, channels: list, commands: list):
        return (
            ((constraint_type == ConstraintTypeEnum.NONE.value) << 2)
            + (bool(channels) << 1)
            + bool(commands)
        )

    @classmethod
    def gen_error_message(cls, constraint_type: int, roles: list[Role]) -> str:
        ctype = {0: 'none of', 1: 'any of', 2: 'all of'}[constraint_type]
        role_names = ' '.join([tag_literal('role', r.snowflake) for r in roles])
        return f'{strong(ctype)} {role_names}'

    def from_dict(self, data: dict):
        self.name = data['name']
        self.type = data['type']
        channels = data['channels']
        commands = data['commands']
        roles = data['roles']
        specificity = self.calc_specificity(self.type, channels, commands)
        error_message = self.gen_error_message(self.type, roles)
        self.specificity = specificity
        self.error_msg = error_message
        self.save()
        self.channels.set(channels)
        self.commands.set(commands)
        self.roles.set(roles)

    class Meta:
        verbose_name = 'command constraint'


class Blacklisted(Entity):
    class Meta:
        verbose_name = 'blacklisted entity'
        verbose_name_plural = 'blacklisted entities'


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
