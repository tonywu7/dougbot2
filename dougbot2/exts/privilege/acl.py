# acl.py
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
from discord.ext.commands import Context, Group
from django.db.models import Q
from more_itertools import bucket

from ...utils.common import is_direct_message
from .exceptions import ACLFailure
from .models import AccessControl, RoleModifier


def applicable(ac: AccessControl, roles: set[int]) -> bool:
    """Check whether this rule applies to someone with these roles."""
    target = set(ac.roles)
    applicable = not target
    if not applicable:
        if ac.modifier == RoleModifier.NONE.value:
            applicable = not (target & roles)
        elif ac.modifier == RoleModifier.ANY.value:
            applicable = bool(target & roles)
        elif ac.modifier == RoleModifier.ALL.value:
            applicable = roles.issuperset(target)
    return applicable


def acl_filter(acls: list[AccessControl], command: str, channel: int, category: int) -> list[AccessControl]:
    """Find all rules applicable to this command and channel."""
    return [r for r in acls if (r.command == command or not r.command)
            and (r.channel == channel or r.channel == category or not r.channel)]


def acl_test(acls: list[AccessControl], roles: set[int]) -> list[AccessControl]:
    """Return the first set of rules that would prevent someone\
    with these roles from using the command.

    If any rules allow this person to use the command,
    this function returns an empty list without further
    processing.
    """
    acls = bucket(acls, lambda c: c.calc_specificity())
    for level in sorted(acls, reverse=True):
        tests = [c for c in acls[level] if applicable(c, roles)]
        if not tests:
            continue
        if any(c.enabled for c in tests):
            return []
        return tests
    return []


async def acl_check(ctx: Context) -> bool:
    """Check this message against access control rules for this server\
    to determine whether this user can use this command."""
    if is_direct_message(ctx):
        return True
    cmd = ctx.command
    if cmd.hidden:
        return True
    if isinstance(cmd, Group) and not cmd.invoke_without_command:
        return True
    author = ctx.message.author
    if author.guild_permissions.administrator:
        return True
    if author == ctx.message.guild.owner:
        return True
    roles = {r.id for r in author.roles}

    @sync_to_async
    def eval_acl() -> list[AccessControl]:
        channel = ctx.channel
        acls: list[AccessControl] = [*(
            AccessControl.objects
            .filter(server_id__exact=ctx.guild.id)
            .filter(
                Q(command__exact=cmd.qualified_name)
                | Q(command__exact=''),
            )
            .filter(
                Q(channel__exact=channel.id)
                | Q(channel__exact=channel.category_id)
                | Q(channel__exact=0),
            )
            .all()
        )]
        return acl_test(acls, roles)

    result = await eval_acl()
    if result:
        raise ACLFailure(cmd.qualified_name, ctx.channel, result)
    return True