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
    """Get all roles for this guild."""
    get_ctx(req, logout=False).assert_access(access, server_id)
    return Role.objects.filter(guild_id__exact=server_id).all()


def get_role_tzs(req: HttpRequest, server_id: str, access: str) -> tuple[list[int], QuerySet[RoleTimezone]]:
    """Get all role timezones for this guild.

    :param req: Current request context
    :type req: HttpRequest
    :param server_id: The guild's Discord ID
    :type server_id: str
    :param access: Access level the calling function needs;
    this ensures that the current request has appropriate authorization
    to see role timezones
    :type access: str
    :return: Query result as a tuple of
    (IDs of all roles in the guild, QuerySet of RoleTimezone objects)
    :rtype: tuple[list[int], QuerySet[RoleTimezone]]
    """
    roles: list[int] = get_roles(req, server_id, access).values_list('snowflake', flat=True)
    zones = RoleTimezone.objects.filter(role_id__in=roles)
    return roles, zones


def set_role_tzs(req: HttpRequest, server_id: str, timezones: dict[int, str]) -> list[RoleTimezone]:
    """Update role timezones for this server to reflect the passed in role to timezone mapping.

    Existing role timezones not in the mapping are not deleted (use `del_role_tzs` instead)
    """
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
    """Delete the role timezones whose role IDs are in the list."""
    get_role_tzs(req, server_id, 'write')[1].filter(role_id__in=roles).delete()
