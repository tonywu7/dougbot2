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

import inflect
from django.db import models
from django.db.models import CASCADE
from polymorphic.models import PolymorphicModel

inflection = inflect.engine()


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
            __dict__ = {k: v for k, v in __dict__.items() if k[0] != '_'}
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


class Entity(NamingMixin, PolymorphicModel, SubclassMetaMixin):
    snowflake: int = models.IntegerField(verbose_name='id', primary_key=True, db_index=True)


class User(Entity):
    name: str = models.CharField(max_length=120, verbose_name='username')
    discriminator: int = models.IntegerField()


class Server(Entity):
    prefix: str = models.CharField(max_length=16, default='t;')


class Channel(Entity):
    name: str = models.CharField(max_length=120)
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='channels')


class Member(Entity):
    nickname: str = models.CharField(max_length=64, blank=True)
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='members')
    profile: User = models.ForeignKey(User, on_delete=CASCADE, related_name='memberships')


class Role(Entity):
    name: str = models.CharField(max_length=120)
    color: int = models.IntegerField()
    guild: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='roles')
