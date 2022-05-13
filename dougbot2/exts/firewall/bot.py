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
from typing import Literal, Optional, Union

from discord import Member, Role, TextChannel, User
from discord.ext.commands import Cog, command, is_owner

from ...blueprints import Surroundings
from ...utils import dm
from ...utils.common import a, code
from ...utils.converters import Constant
from .. import autodoc as doc
from .gatekeeper import Gatekeeper


class Firewall(Cog):
    def __init__(self) -> None:
        self._gatekeeper = Gatekeeper()

    async def intercept(self, event_name: str, *args, **kwargs) -> bool:
        return await self._gatekeeper.handle(event_name, *args, **kwargs)

    async def bot_check_once(self, ctx: Surroundings) -> bool:
        """Check preconditions applicable before any other checks.

        Check if the cog is marked as disabled on the web console.
        Check if the command can be run in DMs (if the context is a DM context).
        """
        for check in asyncio.as_completed(
            [
                dm.dm_allowed_check(ctx),
            ]
        ):
            if not await check:
                return False
        return True

    @command("444")
    @doc.description("Globally forbid an entity from interacting with the bot.")
    @doc.discussion(
        "Detail",
        (
            f'All command invocations are ignored and all events (including {code("on_message")})'
            " are silently dropped.\nThe name of this command comes from nginx's"
            f' {a("HTTP 444", "https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#nginx")}'
            " status code."
        ),
    )
    @doc.restriction(is_owner)
    @doc.hidden
    async def _blacklist(
        self,
        ctx: Surroundings,
        entity: Union[User, Member, Role, TextChannel],
        free: Optional[Constant[Literal["free"]]],
    ):
        if free:
            await self._gatekeeper.discard(entity)
            return await ctx.respond().success().run()
        else:
            await self._gatekeeper.gatekeeper.add(entity)
            msg = f"All events from entity {code(entity)} will be dropped."
            return await ctx.respond(msg).run()
