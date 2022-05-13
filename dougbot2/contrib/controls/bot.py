# bot.py
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


from typing import Literal, Optional

from discord import Activity, ActivityType
from discord.ext.commands import has_guild_permissions, is_owner
from more_itertools import first

from dougbot2.blueprints import Surroundings
from dougbot2.discord import Gear, command, topic
from dougbot2.exceptions import NotAcceptable
from dougbot2.exts import autodoc as doc
from dougbot2.models import Server
from dougbot2.utils.converters import Choice
from dougbot2.utils.markdown import code, escape_markdown, strong


class Controls(
    Gear,
    name="Control panel",
    order=101,
    description="Manage bot settings.",
):
    @topic("prefix")
    @doc.description("Get the command prefix for the bot in this server.")
    @doc.invocation((), "Print the prefix.")
    async def get_prefix(self, ctx: Surroundings):
        prefix = await ctx.bot.get_prefix(ctx.message)
        if isinstance(prefix, list):
            prefix = first(prefix)
        prefix = escape_markdown(prefix)
        example = f'Example: {strong(f"{prefix}help")}'
        await ctx.respond(f"Prefix is {strong(prefix)}\n{example}").run()

    @get_prefix.command("set")
    @doc.description("Set a new prefix for this server.")
    @doc.argument("prefix", "The new prefix to use. Spaces will be trimmed.")
    @doc.example("?", f'Set the command prefix to {code("?")}')
    @doc.restriction(has_guild_permissions, manage_guild=True)
    async def set_prefix(self, ctx: Surroundings, prefix: str):
        server = await Server.get(self.guild)
        try:
            await server.set_prefix(prefix)
            await ctx.respond(
                f"Prefix has been changed to {code(escape_markdown(prefix))}"
            )
        except ValueError as e:
            raise NotAcceptable(e.message)

    async def set_presence(self, kind: str, **kwargs):
        """Set the bot's presence and persist it in the redis cache."""
        bot = self.bot
        set_presence = bot.get_option("set_presence", True)
        if not set_presence:
            return
        if kind == "reset":
            await bot.change_presence(activity=None)
            bot.del_cache(type=f"{__name__}.activity")
            return
        try:
            presence_t = getattr(ActivityType, kind)
        except AttributeError:
            return
        activity = Activity(type=presence_t, **kwargs)
        bot.set_cache((kind, kwargs), None, type=f"{__name__}.activity")
        await bot.change_presence(activity=activity)

    async def resume_presence(self):
        """Restore the bot's presence if one is found in the cache."""
        bot = self.bot
        set_presence = bot.get_option("set_presence", True)
        if not set_presence:
            return
        kind, kwargs = bot.get_cache((None, None), type=f"{__name__}.activity")
        if kind is None:
            return await self.set_presence("reset")
        await self.set_presence(kind, **kwargs)

    @command("status")
    @doc.description("Change the bot's status.")
    @doc.argument("activity", "The type of activity.")
    @doc.argument("name", "The description of the status.")
    @doc.restriction(is_owner)
    @doc.hidden
    async def status(
        self,
        ctx: Surroundings,
        activity: Choice[
            Literal["playing", "watching", "listening", "streaming", "reset"]
        ],
        *,
        name: str = "",
        url: Optional[str] = None,
    ):
        if activity != "reset" and not name:
            raise NotAcceptable("Activity name cannot be empty.")
        await self.set_presence(activity, name=name, url=url)
        return await ctx.respond().success().run()
