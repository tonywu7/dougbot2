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

from graphene import (Argument, Boolean, Enum, Field, InputObjectType, Int,
                      List, ObjectType, String)
from more_itertools import bucket, first

from ...models import Server
from ...schema import ServerMutation
from .models import AccessControl, ACLAction, ACLRoleModifier


class AccessControlType(ObjectType):
    name: str = String()
    commands: list[str] = List(String)
    channels: list[str] = List(String)
    roles: list[str] = List(String)
    modifier: int = Field(Enum.from_enum(ACLRoleModifier))
    action: str = Field(Enum.from_enum(ACLAction))
    specificity: list[int] = List(Int)
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


class ACLDeleteMutation(ServerMutation):
    class Meta:
        model = Server

    class Arguments:
        names = Argument(List(String), default_value=())

    success: bool = Boolean()

    @classmethod
    def mutate(cls, root, info, item_id: str, names: list[str]):
        server = cls.get_instance(info.context, item_id)
        instances = server.acl.all().filter(name__in=names)
        instances.delete()
        return cls(success=True)


class ACLUpdateMutation(ServerMutation):
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
            roles = [int(s) for s in acl.roles]
            commands = acl.commands or ['']
            channels = acl.channels or [0]
            targets = {(cmd, int(ch)): True for cmd, ch
                       in product(commands, channels)}
            for cmd, ch in targets:
                obj = AccessControl(
                    server_id=server.snowflake, name=acl.name,
                    command=cmd, channel=ch,
                    roles=roles, modifier=acl.modifier,
                    action=acl.action, error=acl.error or '',
                )
                obj.calc_specificity()
                instances.append(obj)
        AccessControl.objects.bulk_create(instances)
        return instances

    @classmethod
    def mutate(cls, root, info, item_id: str, changes):
        server = cls.get_instance(info.context, item_id)
        cls.delete(server, changes)
        instances = cls.create(server, changes)
        acl = AccessControlType.serialize(instances)
        return cls(acl=acl)
