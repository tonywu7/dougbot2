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

from datetime import datetime, timedelta, timezone
from typing import Optional

from asgiref.sync import sync_to_async
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _

from telescope2.discord.fetch import DiscordFetch, create_session
from telescope2.utils.datetime import utcnow


@deconstructible
class DiscordUsernameValidator(validators.RegexValidator):
    regex = r'^[^@#:`]+#\d{4}\Z'
    message = 'Enter a valid Discord tag, such as "Clyde#0001".'
    flags = 0


class User(AbstractUser):
    username_validator = DiscordUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_('Required. Valid Discord tag only.'),
        validators=[username_validator],
        error_messages={
            'unique': _('A user with that username already exists.'),
        },
    )

    snowflake: int = models.IntegerField(editable=False, verbose_name='Discord ID', primary_key=True)

    access_token: str = models.CharField(max_length=512, blank=True)
    refresh_token: str = models.CharField(max_length=512, blank=True)
    expires_at: float = models.FloatField(null=True)

    REQUIRED_FIELDS = ['snowflake']

    @property
    def token_expired(self) -> bool:
        if not self.expires_at:
            return None
        return datetime.fromtimestamp(self.expires_at, tz=timezone.utc) <= utcnow()

    async def fresh_token(self) -> Optional[str]:
        expired = self.token_expired
        if expired is None:
            return None
        if expired is False:
            return self.access_token
        if not self.refresh_token:
            return None
        fetch = DiscordFetch(create_session())
        data = await fetch.refresh_tokens(self.refresh_token)
        await fetch.close()
        if not data:
            return None
        self.access_token = data['access_token']
        self.refresh_token = data['refresh_token']
        self.expires_at = (utcnow() + timedelta(seconds=int(data['expires_in']))).timestamp()
        await sync_to_async(self.save)()
        return self.access_token


def read_access_required(f):
    return permission_required(['discord.view_server'])(f)


def write_access_required(f):
    return permission_required([
        'discord.add_server',
        'discord.change_server',
        'discord.delete_server',
    ])(f)
