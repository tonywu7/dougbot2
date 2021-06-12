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

from django.db import models
from django.db.models import CASCADE


class User(models.Model):
    snowflake: int = models.IntegerField(verbose_name='id', primary_key=True, db_index=True)
    name: str = models.CharField(max_length=120, verbose_name='username')
    discriminator: int = models.IntegerField()

    timezone: str = models.CharField(max_length=64, blank=True)


class Server(models.Model):
    snowflake: int = models.IntegerField(verbose_name='id', primary_key=True, db_index=True)

    prefix: str = models.CharField(max_length=16, default='t;')

    class Meta:
        verbose_name = 'guild preference'


class Channel(models.Model):
    snowflake: int = models.IntegerField(verbose_name='id', primary_key=True, db_index=True)
    name: str = models.CharField(max_length=120)

    server: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='channels')


class Member(models.Model):
    snowflake: int = models.IntegerField(verbose_name='id', primary_key=True, db_index=True)
    nickname: str = models.CharField(max_length=64, blank=True)

    server: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='members')
    user: User = models.ForeignKey(User, on_delete=CASCADE, related_name='memberships')


class Role(models.Model):
    snowflake: int = models.IntegerField(verbose_name='id', primary_key=True, db_index=True)
    name: str = models.CharField(max_length=120)
    color: int = models.IntegerField()

    server: Server = models.ForeignKey(Server, on_delete=CASCADE, related_name='roles')

    timezone: str = models.CharField(max_length=64, blank=True)
