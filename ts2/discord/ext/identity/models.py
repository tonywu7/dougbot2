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

from datetime import datetime

import discord
import pytz
from asgiref.sync import sync_to_async
from django.conf.locale import LANG_INFO
from django.db import models
from django.db.models import CASCADE
from timezone_field import TimeZoneField

from ...models import Entity, ModelTranslator, Server


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


LocaleType = make_locale_type()


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
                val = dict(field.choices).get(val, val)
            info[field.verbose_name] = val
        return info

    def format_datetime(self, dt: datetime):
        return dt.strftime(self.datetimefmt)


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
