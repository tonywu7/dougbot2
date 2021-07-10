# constraints.py
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

from typing import Literal

import attr
import discord
from asgiref.sync import sync_to_async
from discord import Member, TextChannel
from discord.ext.commands.errors import CheckFailure
from django.db.models.query import Q
from more_itertools import bucket

from ts2.utils.lang import either_or

from .context import Circumstances
from .errors import explains
from .models import CommandConstraint, ConstraintType, id_dot
from .utils.markdown import strong, tag


async def command_constraints_check(ctx: Circumstances) -> bool:
    author = ctx.message.author
    if author.guild_permissions.administrator:
        return True
    if author == ctx.message.guild.owner:
        return True

    @sync_to_async
    def eval_constraints() -> Literal[True] | list[CommandCondition]:
        constraints = (
            CommandConstraint.objects.all()
            .filter(collection_id=ctx.guild.id)
            .filter(Q(commands__identifier__exact=ctx.invoked_with) | Q(commands=None))
            .filter(Q(channels__pk=ctx.channel.id) | Q(channels=None))
        )
        tests = CommandCriteria([CommandCondition.from_model(c) for c in constraints])
        return tests(author)

    result = await eval_constraints()
    if result is not True:
        raise ConstraintFailure(ctx.invoked_with, author, ctx.channel, result)
    return True


def _int_set(s):
    return {int(n) for n in s}


@attr.s
class CommandCondition:
    type: ConstraintType = attr.ib()
    specificity: int = attr.ib()
    roles: set[int] = attr.ib(converter=_int_set)

    commands: set = attr.ib(converter=_int_set, factory=set)
    channels: set = attr.ib(converter=_int_set, factory=set)
    error: str = attr.ib(default='')

    def __call__(self, member: discord.Member) -> bool:
        return self.test({id_dot(r) for r in member.roles})

    def test(self, roles: set[int]) -> bool:
        if self.type is ConstraintType.NONE.value:
            return not (self.roles & roles)
        elif self.type is ConstraintType.ANY.value:
            return bool(self.roles & roles)
        elif self.type is ConstraintType.ALL.value:
            return (self.roles & roles) == self.roles

    @classmethod
    def from_model(cls, model: CommandConstraint):
        return cls(
            type=model.type,
            specificity=model.specificity,
            error=model.error_msg,
            roles=model.roles.values_list('snowflake', flat=True).all(),
        )

    @classmethod
    def deserialize(cls, data: dict):
        kind, channels, commands = data['type'], data['channels'], data['commands']
        specificity = CommandConstraint.calc_specificity(kind, channels, commands)
        return cls(kind, specificity, data['roles'], commands=commands, channels=channels)


@attr.s
class CommandCriteria:
    criteria: list[CommandCondition] = attr.ib(converter=list)

    def __call__(self, member: discord.Member) -> bool:
        roles = {id_dot(r) for r in member.roles}
        return self.test(roles)

    def test(self, roles: set[int]) -> Literal[True] | list[CommandCondition]:
        sorted_criteria = bucket(self.criteria, lambda c: c.specificity)
        for specificity in sorted(sorted_criteria, reverse=True):
            tests = [*sorted_criteria[specificity]]
            if not any(c.test(roles) for c in tests):
                return tests
        return True


class ConstraintFailure(CheckFailure):
    def __init__(self, invocation: str, author: Member, channel: TextChannel,
                 conditions: list[CommandCondition], *args):
        invocation = strong(invocation)
        channel = tag(channel)
        message = (f'{tag(author)} attempted to use disallowed command {invocation} in {channel}')
        super().__init__(message=message, *args)
        self.message = message
        conditions = [f'have {c.error}' for c in conditions]
        head = f'To use {invocation} in {channel}, your roles must'
        sep = ',\n'
        if len(conditions) == 1:
            self.reply = f'{head} {conditions[0]}'
        else:
            self.reply = f'{head}:\n{either_or(*conditions, sep=sep)}'

    def __str__(self) -> str:
        return self.message


@explains(ConstraintFailure, 'Missing roles', 0)
async def on_constraint_failure(ctx, exc):
    return exc.reply, 30
