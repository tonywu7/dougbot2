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
from typing import Optional

import discord
import pendulum
import pytz
from django.conf.locale import LANG_INFO
from django.db import models
from django.db.models import CASCADE
from timezone_field import TimeZoneField

from ...models import Entity, ModelTranslator, Server
from ...utils.async_ import async_get, async_save


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
    datetimefmt: str = models.TextField('datetime format', blank=True, default='D MMM YYYY h:mm:ss A')
    locale: str = models.CharField('language', max_length=120, blank=True, default='en', choices=LocaleType.choices)

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
    async def async_get(cls, user: discord.User) -> User:
        try:
            return await async_get(cls.objects, snowflake=user.id)
        except cls.DoesNotExist:
            return cls(snowflake=user.id, name=user.name,
                       discriminator=user.discriminator)

    async def async_save(self, *args, **kwargs):
        return await async_save(self, *args, **kwargs)

    async def save_timezone(self, tz: pytz.BaseTzInfo | str):
        self.timezone = tz
        await self.async_save()

    @property
    def isdefault(self):
        return self._default

    def gettime(self, aware_required=False) -> datetime:
        if not self.timezone and aware_required:
            raise ValueError('User does not have a timezone.')
        return datetime.now(tz=self.timezone)

    def format_prefs(self) -> dict[str, str]:
        info = {}
        for field_name in ('timezone', 'datetimefmt', 'locale'):
            field = self._meta.get_field(field_name)
            val = getattr(self, field_name)
            if field.choices:
                val = dict(field.choices).get(val, val)
            info[field.verbose_name] = val
        return info

    def format_datetime(self, dt: Optional[datetime] = None):
        dt = dt or self.gettime()
        fmt = self.datetimefmt
        if fmt[:9] == 'strftime:':
            return dt.strftime(fmt[9:])
        return pendulum.instance(dt).format(self.datetimefmt)


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
