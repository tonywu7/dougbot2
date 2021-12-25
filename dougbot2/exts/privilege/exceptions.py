# exceptions.py
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

from discord import TextChannel
from discord.ext.commands import CheckFailure

from ...utils.markdown import strong, tag
from ..logging import ignore_exception
from .models import AccessControl


@ignore_exception
class ACLFailure(CheckFailure):
    """Exception for when a user fails the access control test and\
    is therefore not allowed to use the command."""

    def __init__(self, invocation: str, channel: TextChannel,
                 conditions: list[AccessControl], *args):
        invocation = strong(invocation)
        channel = tag(channel)
        self.call = invocation
        self.message = f'Call to {invocation} in {channel} did not satisfy ACLs.'
        super().__init__(message=self.message, *args)
        self.errors = [c.error for c in conditions if c.error]

    def __str__(self) -> str:
        return self.message


async def _on_acl_failure(ctx, exc: ACLFailure):
    msg = f'You cannot use {exc.call} in this channel.'
    for e in exc.errors:
        msg = f'{msg}\n{e}'
    return msg


def setup_alerts(bot):
    return {
        ACLFailure: {
            'handler': _on_acl_failure,
            'alerts': [
                'Command restriction',
                'HTTP 403 Forbidden',
                'You Shall Not Pass.',
                "Sorry, you can't do that in here.",
                'Nope.',
                'Nah.',
                'Not a chance.',
                "Don't even think about it.",
            ],
        }
    }
