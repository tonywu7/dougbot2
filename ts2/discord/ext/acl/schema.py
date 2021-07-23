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

from itertools import product
from typing import Optional, Union

from graphene import (ID, Argument, Boolean, Enum, Field, InputObjectType, Int,
                      List, NonNull, ObjectType, String)
from more_itertools import bucket, first

from ts2.discord.middleware import get_server

from ...models import Server
from ...schema import ServerModelMutation
from .models import AccessControl, ACLAction, ACLRoleModifier


class AccessControlType(ObjectType):
    name: str = Field(String, required=True)
    commands: list[str] = List(NonNull(String))
    channels: list[str] = List(NonNull(String))
    roles: list[str] = List(NonNull(String))
    modifier: int = Field(Enum.from_enum(ACLRoleModifier), required=True)
    action: str = Field(Enum.from_enum(ACLAction), required=True)
    specificity: list[int] = List(NonNull(Int))
    error: str = String()

    @classmethod
    def serialize(cls, acl: list[AccessControl]):
        acls = bucket(acl, lambda c: c.name)
        objs = []
        for name in acls:
            instances = [*acls[name]]
            cmds = {c.command for c in instances if c.command}
            channels = {str(c.channel) for c in instances if c.channel}
            instance = first(instances)
            roles = [str(r) for r in instance.roles]
            modifier = instance.modifier
            action = instance.action
            specificity = instance.calc_specificity()
            error = instance.error
            objs.append(AccessControlType(
                name=name, commands=cmds, channels=channels,
                roles=roles, modifier=modifier, action=action,
                specificity=specificity, error=error,
            ))
        return objs


class AccessControlInput(InputObjectType):
    name: str = Field(String, required=True)
    commands: list[str] = Field(List(String), default_value=())
    channels: list[str] = Field(List(String), default_value=())
    roles: list[str] = Field(List(String), default_value=())
    modifier: int = Field(Enum.from_enum(ACLRoleModifier), required=True)
    action: str = Field(Enum.from_enum(ACLAction), required=True)
    error: str = Field(String)


def schema_to_models(
    self: Union[AccessControlType, AccessControlInput],
    server_id: Optional[int] = None,
) -> list[AccessControl]:
    roles = [int(s) for s in self.roles]
    commands = self.commands or ['']
    channels = self.channels or [0]
    targets = {(cmd, int(ch)): True for cmd, ch
               in product(commands, channels)}
    instances = []
    for cmd, ch in targets:
        obj = AccessControl(
            server_id=server_id, name=self.name,
            command=cmd, channel=ch,
            roles=roles, modifier=self.modifier,
            action=self.action, error=self.error or '',
        )
        obj.calc_specificity()
        instances.append(obj)
    return instances


class ACLDeleteMutation(ServerModelMutation):
    class Meta:
        model = Server

    class Arguments:
        names = Argument(List(String), default_value=())

    success: bool = Boolean()

    @classmethod
    def mutate(cls, root, info, server_id: str, names: list[str]):
        server = cls.get_instance(info.context, server_id)
        instances = server.acl.all().filter(name__in=names)
        instances.delete()
        return cls(success=True)


class ACLUpdateMutation(ServerModelMutation):
    class Meta:
        model = Server

    class Arguments:
        changes = Argument(List(AccessControlInput), default_value=())

    acl = List(AccessControlType)

    @classmethod
    def delete(cls, server: Server, changes: list[AccessControlInput]):
        names = [acl.name for acl in changes]
        existing = server.acl.all().filter(name__in=names)
        existing.delete()

    @classmethod
    def create(cls, server: Server, changes: list[AccessControlInput]) -> list[AccessControl]:
        instances = []
        for acl in changes:
            instances.extend(schema_to_models(acl, server.snowflake))
        AccessControl.objects.bulk_create(instances)
        return instances

    @classmethod
    def mutate(cls, root, info, server_id: str, changes):
        server = cls.get_instance(info.context, server_id)
        cls.delete(server, changes)
        instances = cls.create(server, changes)
        acl = AccessControlType.serialize(instances)
        return cls(acl=acl)


class ACLQuery(ObjectType):
    acl = List(AccessControlType, server_id=ID(required=True))

    @classmethod
    def resolve_acl(cls, root, info, server_id):
        server = get_server(info.context, server_id)
        return AccessControlType.serialize([*server.acl.all()])


class ACLMutation(ObjectType):
    delete_acl = ACLDeleteMutation.Field(name='deleteACL')
    update_acl = ACLUpdateMutation.Field(name='updateACL')
