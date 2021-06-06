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

from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.db import models
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy as _


@deconstructible
class DiscordUsernameValidator(validators.RegexValidator):
    regex = r'^[^@#:`]+#\d{4}\Z'
    message = (
        'Enter a valid Discord tag, such as "Clyde#0001".'
    )
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

    discord_id: int = models.IntegerField(editable=False, verbose_name='Discord ID')
    oauth2_refresh: str = models.CharField(max_length=512, blank=True)

    REQUIRED_FIELDS = ['discord_id']
