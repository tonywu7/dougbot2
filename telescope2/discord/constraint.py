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

from asgiref.sync import sync_to_async
from discord import Member, TextChannel
from discord.ext.commands.errors import CheckFailure
from django.db.models.query import Q

from .context import Circumstances
from .models import CommandConstraint, CommandCriteria
from .utils.textutil import strong, tag


async def command_constraints_check(ctx: Circumstances) -> bool:
    author = ctx.message.author
    if author.guild_permissions.administrator:
        return True
    if author == ctx.message.guild.owner:
        return True

    @sync_to_async
    def eval_constraints():
        constraints = (
            CommandConstraint.objects.all()
            .filter(collection_id=ctx.guild.id)
            .filter(Q(commands__identifier__exact=ctx.invoked_with) | Q(commands=None))
            .filter(Q(channels__pk=ctx.channel.id) | Q(channels=None))
        )
        tests = CommandCriteria([c.to_dataclass() for c in constraints])
        return tests(author)

    result = await eval_constraints()
    if not result:
        raise ConstraintFailure(ctx.invoked_with, author, ctx.channel)
    return True


class ConstraintFailure(CheckFailure):
    def __init__(self, invocation: str, author: Member, channel: TextChannel, *args):
        message = (f'{tag(author)} attempted to use disallowed command {strong(invocation)} '
                   f'in {tag(channel)}')
        super().__init__(message=message, *args)
