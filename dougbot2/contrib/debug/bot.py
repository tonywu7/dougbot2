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

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import psutil
from discord import Message
from discord.ext.commands import BucketType, is_owner

from dougbot2.blueprints import Surroundings
from dougbot2.discord import Gear, command, group
from dougbot2.exts import autodoc as doc
from dougbot2.settings.versions import list_versions
from dougbot2.utils.common import (
    Embed2,
    can_embed,
    code,
    em,
    strong,
    utcnow,
    utctimestamp,
)
from dougbot2.utils.dm import accept_dms
from dougbot2.utils.pagination import chapterize_items

from .converters import LoggingLevel


class Debug(
    Gear,
    name="Debug",
    order=95,
    description="",
):
    """Cog for internal debugging commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command("about")
    @doc.description("Print info about the bot.")
    @can_embed
    async def about_command(self, ctx: Surroundings, *, rest: str = None):
        versions = " ".join([code(f"{pkg}/{v}") for pkg, v in list_versions().items()])
        info = await ctx.bot.application_info()
        embed = (
            Embed2(title=info.name, description=info.description)
            .add_field(name="Versions", value=versions, inline=False)
            .set_thumbnail(url=info.icon_url)
            .personalized(ctx.me)
        )
        return await ctx.respond(embed=embed).run()

    @command("echo")
    @accept_dms
    @doc.description("Send the command arguments back.")
    @doc.argument("text", "Message to send back.")
    @doc.example("The quick brown fox", em('sends back "The quick brown fox"'))
    async def echo(self, ctx: Surroundings, *, text: str = None):
        if not text:
            await ctx.respond(ctx.message.content).reply().run()
        else:
            await ctx.respond(text).reply().run()

    @command("stderr", aliases=("log",))
    @doc.description("Send a message into the bot's log file.")
    @doc.argument("level", f'{code("logging")} levels e.g. {code("INFO")}.')
    @doc.argument("text", "The message to log.")
    @doc.restriction(is_owner)
    @doc.hidden
    async def _log(
        self, ctx: Surroundings, level: Optional[LoggingLevel] = None, *, text: str = ""
    ):
        if isinstance(level, str):
            text = f"{level} {text}"
            level = logging.INFO
        elif level is None:
            level = logging.INFO
        if not text:
            msg = ctx.message.content
        else:
            msg = text
        await ctx.get_logger().log(level, msg)
        await ctx.respond().success().run()

    @command("throw")
    @doc.description("Throw an exception inside the command handler.")
    @doc.restriction(is_owner)
    @doc.cooldown(1, 10, BucketType.user)
    @doc.hidden
    async def _throw(self, ctx: Surroundings, *, args: str = None):
        return {}[None]

    @command("overflow")
    @doc.description(f'Throw a {code("RecursionError")}.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _overflow(self, ctx: Surroundings, *, args: str = None):
        return await self._overflow(ctx, args=args)

    @command("kill")
    @doc.description(
        "Try to kill the bot by attempting an irrecoverable stack overflow."
    )
    @doc.argument("sig", f'Either {strong("SIGTERM")} or {strong("SIGKILL")}.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _kill(self, ctx: Surroundings, *, sig: str = None):
        async with ctx.typing():
            if sig == "SIGKILL":
                return psutil.Process(os.getpid()).kill()
            elif sig == "SIGTERM":
                return psutil.Process(os.getpid()).terminate()
            return await self._do_kill(ctx, sig)

    async def _do_kill(self, ctx, *args, **kwargs):
        return await self._do_kill(ctx, *args, **kwargs)

    @command("sleep")
    @doc.description("Suspend the handler coroutine for some duration.")
    @doc.concurrent(2, BucketType.user, wait=False)
    @doc.hidden
    async def _sleep(self, ctx: Surroundings, duration: Optional[float] = 10):
        async with ctx.typing():
            await asyncio.sleep(duration)

    @command("ping")
    @doc.description("Test the network latency between the bot and Discord.")
    async def ping(self, ctx: Surroundings):
        await ctx.send(f":PONG {utctimestamp()}")

    @Gear.listener("on_message")
    async def on_ping(self, msg: Message):
        bot = self.bot
        gateway_dst = utctimestamp()

        if not bot.user:
            return
        if bot.user.id != msg.author.id:
            return
        if msg.content[:6] != ":PONG ":
            return

        try:
            msg_created = float(msg.content[6:])
        except ValueError:
            return

        gateway_latency = 1000 * (gateway_dst - msg_created)
        edit_start = utcnow()
        await msg.edit(
            content=f"Gateway (http send -> gateway receive time): {gateway_latency:.3f}ms"
        )
        edit_latency = (utcnow() - edit_start).total_seconds() * 1000

        await msg.edit(
            content=(
                f'Gateway: {code(f"{gateway_latency:.3f}ms")}'
                f'\nHTTP API (Edit): {code(f"{edit_latency:.3f}ms")}'
            )
        )

    @group("debug", case_insensitive=True, invoke_without_command=False)
    @doc.restriction(is_owner)
    @doc.hidden
    async def debug_cmd(self, ctx: Surroundings):
        return

    @debug_cmd.command("cmdlist")
    @doc.hidden
    async def debug_cmdlist(self, ctx: Surroundings):
        manpage = ctx.bot.manpage
        cmds = [
            f"{i}. {s}"
            for i, s in enumerate(
                sorted([cmd for cmd, p in manpage.iter_commands()]), start=1
            )
        ]
        for chunk in chapterize_items(cmds, 1440):
            await ctx.send("\n".join(chunk))

    @debug_cmd.command("docs")
    @doc.hidden
    async def debug_docs(
        self, ctx: Surroundings, start: Optional[int] = None, end: Optional[int] = None
    ):
        manpage = ctx.bot.manpage

        pages = [
            manpage.to_embed(),
            *[p.to_embed() for cmd, p in manpage.iter_commands()],
        ]
        for page in pages[start:end]:
            for i in range(len(page.content)):
                body = page.get_embed(i)
                await ctx.send(embed=body)

        await ctx.send(ctx.styles.emotes.success)
