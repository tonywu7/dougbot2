# timezone.py
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

from django.db.models import QuerySet
from django.http import HttpRequest

from ts2.discord.middleware import get_ctx
from ts2.discord.models import Role

from .models import RoleTimezone


def get_roles(req: HttpRequest, server_id: str, access: str) -> QuerySet[Role]:
    get_ctx(req, logout=False).assert_access(access, server_id)
    return Role.objects.filter(guild_id__exact=server_id).all()


def get_role_tzs(req: HttpRequest, server_id: str, access: str) -> tuple[list[int], QuerySet[RoleTimezone]]:
    roles: list[int] = get_roles(req, server_id, access).values_list('snowflake', flat=True)
    zones = RoleTimezone.objects.filter(role_id__in=roles)
    return roles, zones


def set_role_tzs(req: HttpRequest, server_id: str, timezones: dict[int, str]) -> list[RoleTimezone]:
    roles, zones = get_role_tzs(req, server_id, 'write')
    zones = zones.filter(role_id__in=timezones)
    for z in zones:
        tz = timezones.pop(z.role_id)
        z.timezone = tz

    to_create: list[RoleTimezone] = []
    for k, v in timezones.items():
        to_create.append(RoleTimezone(role_id=k, timezone=v))
    if to_create:
        roles = set(roles)
        to_create = [tz for tz in to_create if tz.role_id in roles]
        RoleTimezone.objects.bulk_create(to_create)

    RoleTimezone.objects.bulk_update(zones, ('timezone',))
    return [*to_create, *zones]


def del_role_tzs(req: HttpRequest, server_id: str, roles: list[str]):
    get_role_tzs(req, server_id, 'write')[1].filter(role_id__in=roles).delete()
