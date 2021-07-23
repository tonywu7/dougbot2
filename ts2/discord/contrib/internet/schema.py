# schema.py
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

from graphene import (ID, Argument, Boolean, InputObjectType, List, Mutation,
                      ObjectType, String)
from graphene_django import DjangoObjectType

from .models import RoleTimezone
from .timezone import del_role_tzs, get_role_tzs, set_role_tzs


class RoleTimezoneType(DjangoObjectType):
    role_id = ID(required=True)
    timezone = String(required=True)

    class Meta:
        model = RoleTimezone
        fields = ['role_id', 'timezone']

    @classmethod
    def resolve_role_id(cls, root: RoleTimezone, info):
        return str(root.role.snowflake)

    @classmethod
    def resolve_timezone(cls, root: RoleTimezone, info):
        return str(root.timezone)


class RoleTimezoneInput(InputObjectType):
    role_id = Argument(ID, required=True)
    timezone = Argument(String, required=True)


class RoleTimezoneUpdateMutation(Mutation):
    class Arguments:
        server_id = Argument(ID, required=True)
        timezones = Argument(List(RoleTimezoneInput), default_value=())

    timezones = List(RoleTimezoneType)

    @classmethod
    def mutate(cls, root, info, *, server_id: str, timezones: list[RoleTimezoneInput]):
        timezones = {int(i.role_id): i.timezone for i in timezones}
        updated = set_role_tzs(info.context, server_id, timezones)
        return cls(timezones=updated)


class RoleTimezoneDeleteMutation(Mutation):
    class Arguments:
        server_id = Argument(ID, required=True)
        role_ids = Argument(List(String), default_value=())

    success = Boolean()

    @classmethod
    def mutate(cls, root, info, *, server_id: str, role_ids: list[str]):
        del_role_tzs(info.context, server_id, role_ids)
        return cls(True)


class InternetQuery(ObjectType):
    timezones = List(RoleTimezoneType, server_id=ID(required=True))

    @classmethod
    def resolve_timezones(cls, root, info, server_id: str):
        return get_role_tzs(info.context, server_id)[1]


class InternetMutation(ObjectType):
    update_timezones = RoleTimezoneUpdateMutation.Field()
    delete_timezones = RoleTimezoneDeleteMutation.Field()
