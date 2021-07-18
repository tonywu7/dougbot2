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

from django.db.models import QuerySet
from graphene import (Argument, Boolean, Enum, Field, Int, List, ObjectType,
                      String)
from more_itertools import bucket, first

from ...models import Server
from ...utils.graphql import ModelMutation, input_from_type
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


AccessControlInput = input_from_type(AccessControlType, specificity=False)


class AccessControlMutation:
    @classmethod
    def get_acls(cls, arguments: dict) -> QuerySet[AccessControl]:
        return cls.get_instance(arguments).acl.all()


class ACLDeleteMutation(AccessControlMutation, ModelMutation[Server], model=Server):
    class Arguments:
        name = Argument(String, required=True)

    success: bool = Boolean()

    @classmethod
    def mutate(cls, root, info, **arguments):
        instances = cls.get_acls(arguments).filter(name__exact=arguments['name'])
        instances.delete()
        return cls(success=True)


class ACLUpdateMutation(AccessControlMutation, ModelMutation[Server], model=Server):
    class Arguments:
        changes = List(AccessControlInput)

    acl = List(AccessControlType)

    @classmethod
    def delete(cls, info, **arguments):
        changes: list[AccessControlInput] = arguments['changes']
        names = [acl.name for acl in changes]
        existing = cls.get_acls(arguments).filter(name__in=names)
        existing.delete()

    @classmethod
    def create(cls, info, **arguments) -> list[AccessControl]:
        changes: list[AccessControlInput] = arguments['changes']
        instances = []
        server = cls.get_instance(arguments)
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
    def mutate(cls, root, info, **arguments):
        cls.delete(info, **arguments)
        instances = cls.create(info, **arguments)
        acl = AccessControlType.serialize(instances)
        return cls(acl=acl)
