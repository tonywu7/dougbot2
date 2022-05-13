# bot.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

from discord.ext.commands import command

from dougbot2.blueprints import Surroundings
from dougbot2.discord import Gear
from dougbot2.exceptions import DirectMessageForbidden
from dougbot2.exts import autodoc as doc
from dougbot2.utils.common import accept_dms, can_embed


class Help(
    Gear,
    name="Help desk",
    order=0,
    description="See help & documentations for the bot",
):
    @command("help", aliases=("commands",))
    @accept_dms
    @doc.description("Get help about commands.")
    @doc.argument("query", 'A command name, such as "echo" or "prefix set".')
    @doc.invocation((), "See all commands.")
    @doc.invocation(("query",), "See help for a command.")
    @can_embed
    async def help_command(self, ctx: Surroundings, *, query: str = "") -> None:
        manpage = ctx.bot.manpage
        if not query:
            pagination = manpage.to_embed()
        else:
            include_hidden = await ctx.bot.is_owner(ctx.author)
            pagination = manpage.find_command(query, include_hidden).to_embed()
        res = (
            ctx.respond(embed=pagination)
            .deleter()
            .responder(pagination.with_context(ctx))
        )
        if not query:
            res = res.dm().success()
        delivery = await res.run()
        if res.direct_message and not delivery.message:
            raise DirectMessageForbidden()
