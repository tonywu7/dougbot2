# perms.py
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

import asyncio

from discord.ext.commands import Cog

from ... import cog
from ...context import Circumstances
from ...exts import access_control
from ...utils import dm


class Listener(Cog):
    @Cog.bot_check_once
    async def command_global_check(ctx: Circumstances) -> bool:
        """Check preconditions applicable before any other checks.

        Check if the cog is marked as disabled on the web console.
        Check if the command can be run in DMs (if the context is a DM context.
        """
        for check in asyncio.as_completed([
            cog.cog_enabled_check(ctx),
            dm.dm_allowed_check(ctx),
        ]):
            if not await check:
                return False
        return True

    @Cog.bot_check
    async def command_check(ctx: Circumstances) -> bool:
        """Check preconditions applicable to all commands.

        Check if the member satisfy the command's access control policy.
        """
        for check in asyncio.as_completed([
            access_control.acl_check(ctx),
        ]):
            if not await check:
                return False
        return True
