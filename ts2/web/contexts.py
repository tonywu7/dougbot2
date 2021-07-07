# contexts.py
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

from dataclasses import dataclass
from typing import Optional

from django.apps import apps
from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest

from ts2.discord.fetch import PartialGuild, PartialUser
from ts2.discord.models import Server

from .config import CommandAppConfig, Extensions
from .forms import PreferenceForms


def user_info(req: HttpRequest):
    return {
        'user_authenticated': req.user.is_authenticated,
        'user_superuser': req.user.is_superuser,
    }


def discord_info(req: HttpRequest):
    return {
        'discord': getattr(req, 'discord', None),
    }


def application_info(req: HttpRequest):
    return {
        'branding_full': settings.BRANDING_FULL,
        'branding_short': settings.BRANDING_SHORT,
    }


def site_info(req: HttpRequest):
    site = get_current_site(req)
    return {
        'current_domain': site.domain,
    }


@dataclass
class DiscordContext:
    access_token: str

    user_id: int
    username: str
    is_staff: bool
    is_superuser: bool

    user_profile: PartialUser

    available_servers: dict[int, PartialGuild]
    joined_servers: dict[int, PartialGuild]
    server_id: Optional[int] = None
    server: Optional[Server] = None

    forms: PreferenceForms = None

    def __post_init__(self):
        try:
            self.server_id = int(self.server_id)
        except (TypeError, ValueError):
            self.server_id = None
        self.forms = PreferenceForms(self)

    @property
    def servers(self) -> dict[int, PartialGuild]:
        return {**self.available_servers, **self.joined_servers}

    @property
    def server_joined(self) -> bool:
        return self.current.id in self.joined_servers

    @property
    def current(self) -> Optional[PartialGuild]:
        return self.servers.get(self.server_id)

    @property
    def extension_state(self) -> dict[str, tuple[bool, CommandAppConfig]]:
        extensions: Extensions = apps.get_app_config('discord').extensions
        if not self.server:
            return {label: (False, conf) for label, conf in extensions.items()}
        enabled = self.server.extensions
        return {label: (label in enabled, conf) for label, conf in extensions.items()}
