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
import io
import logging
import os
from typing import Literal, Optional, Union

import psutil
import simplejson as json
from discord import File, Member, Message, MessageReference, Role, TextChannel
from discord.ext.commands import (BucketType, Converter, command, has_role,
                                  is_owner)

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.common import (Constant, Dictionary, JinjaTemplate,
                                    format_exception, get_traceback)
from ts2.discord.ext.template import get_environment
from ts2.discord.utils.markdown import E, a, code, strong
from ts2.utils.datetime import localnow


class LoggingLevel(Converter):

    async def convert(self, ctx: Circumstances, arg: str) -> int | str:
        """Convert a logging level name (e.g. DEBUG) to its int value."""
        level = logging.getLevelName(arg)
        if isinstance(level, int):
            return level
        return arg


class Debugging(
    Gear, name='Debugging', order=95,
    description='',
):
    """Cog for internal debugging commands."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('stderr')
    @doc.description("Send a message into the bot's log file.")
    @doc.argument('level', f'{code("logging")} levels e.g. {code("INFO")}.')
    @doc.argument('text', 'The message to log.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _log(self, ctx: Circumstances, level: Optional[LoggingLevel] = None, *, text: str = ''):
        if isinstance(level, str):
            text = f'{level} {text}'
            level = logging.INFO
        elif level is None:
            level = logging.INFO
        if not text:
            msg = ctx.message.content
        else:
            msg = text
        await ctx.log.log(f'{self.app_label}.log', level, msg)

    @command('throw')
    @doc.description('Throw an exception inside the command handler.')
    @doc.restriction(is_owner)
    @doc.cooldown(1, 10, BucketType.user)
    @doc.hidden
    async def _throw(self, ctx: Circumstances, *, args: str = None):
        return {}[None]

    @command('overflow')
    @doc.description(f'Throw a {code("RecursionError")}.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _overflow(self, ctx: Circumstances, *, args: str = None):
        return await self._overflow(ctx, args=args)

    @command('kill')
    @doc.description('Try to kill the bot by attempting an irrecoverable stack overflow.')
    @doc.argument('sig', f'If equals {code(-9)}, {strong("send SIGKILL instead")} {E("gun")}.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def _kill(self, ctx: Circumstances, *, sig: str = None):
        async with ctx.typing():
            if sig == '-9':
                psutil.Process(os.getpid()).kill()
            return await self._do_kill(ctx, sig)

    async def _do_kill(self, ctx, *args, **kwargs):
        return await self._do_kill(ctx, *args, **kwargs)

    @command('sleep')
    @doc.description('Suspend the handler coroutine for some duration.')
    @doc.concurrent(2, BucketType.user, wait=False)
    @doc.hidden
    async def _sleep(self, ctx: Circumstances, duration: Optional[float] = 10):
        async with ctx.typing():
            await asyncio.sleep(duration)

    @command('isnotinthesudoersfile')
    @doc.description('[Incident](https://xkcd.com/838/)')
    @doc.restriction(has_role, item=0)
    @doc.hidden
    async def _sudo(self, ctx: Circumstances, *, args: str = None):
        await ctx.send(f'{ctx.me} is in the sudoers file!')

    @command('444')
    @doc.description('Globally forbid an entity from interacting with the bot.')
    @doc.discussion('Detail', (
        f'All command invocations are ignored and all events (including {code("on_message")})'
        " are silently dropped.\nThe name of this command comes from nginx's"
        f' {a("HTTP 444", "https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#nginx")}'
        ' status code.'
    ))
    @doc.restriction(is_owner)
    @doc.hidden
    async def _blacklist(self, ctx: Circumstances, entity: Union[Member, Role, TextChannel],
                         free: Optional[Constant[Literal['free']]]):
        if free:
            await ctx.bot.gatekeeper.discard(entity)
        else:
            await ctx.bot.gatekeeper.add(entity)

    @command('ofstream')
    @doc.description('Send the message content back as a text file.')
    @doc.argument('text', 'Text message to send back.')
    @doc.argument('message', 'Another message whose content will be included.')
    @doc.accepts_reply('Include the replied-to message in the file.')
    @doc.use_syntax_whitelist
    @doc.invocation(('message', 'text', 'reply'), None)
    @doc.hidden
    async def ofstream(
        self, ctx: Circumstances,
        message: Optional[Message],
        *, text: str = None,
        reply: Optional[MessageReference] = None,
    ):
        if not message and reply:
            message = reply.resolved
        if not text and not message:
            return
        with io.StringIO() as stream:
            if text:
                stream.write(f'{text}\n\n')
            if message:
                stream.write(f'BEGIN MESSAGE {message.id}\n')
                if message.content:
                    stream.write(f'{message.content}\n')
                for embed in message.embeds:
                    stream.write(json.dumps(embed.to_dict()))
                    stream.write('\n')
            stream.seek(0)
            fname = f'message.{localnow().isoformat().replace(":", ".")}.txt'
            file = File(stream, filename=fname)
            await ctx.send(file=file)

    @command('render')
    @doc.description('Render a Jinja template.')
    @doc.argument('template', 'Jinja template string.')
    @doc.argument('variables', 'Context variables.')
    @doc.use_syntax_whitelist
    @doc.invocation(('template', 'variables'), None)
    async def render(
        self, ctx: Circumstances,
        template: JinjaTemplate,
        variables: Optional[Dictionary],
    ):
        env = get_environment()
        if variables:
            variables = variables.result
        else:
            variables = {}
        async with ctx.typing():
            try:
                txt = await env.render_timed(ctx, template.result, variables)
                return await ctx.send(txt)
            except Exception as e:
                embed = format_exception(e)
                tb = get_traceback(e)
                return await ctx.send(embed=embed, file=tb)
