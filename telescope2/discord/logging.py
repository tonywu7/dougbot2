# logging.py
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

import io
import logging
import sys
import traceback
from functools import partialmethod
from typing import Dict, List, Optional, Tuple, Type, TypedDict

from discord import AllowedMentions, Color, Embed, File, Role, TextChannel
from discord.ext.commands import errors
from discord.utils import escape_markdown

from telescope2.utils.datetime import localnow, utcnow

from . import constraint, extension
from .context import Circumstances
from .utils.textutil import tag, trunc_for_field, unmarked


class _LoggingConf(TypedDict):
    key: str
    name: str
    channel: int
    role: Optional[int]


class _ErrorConf(TypedDict):
    key: str
    name: str
    level: int
    superuser: Optional[bool]


LOGGING_CLASSES: List[_LoggingConf] = []

EXCEPTIONS: Dict[Tuple[Type[Exception], ...], _ErrorConf] = {
    (errors.CommandInvokeError,): {
        'name': 'Uncaught exceptions',
        'key': 'CommandInvokeError',
        'level': logging.ERROR,
        'superuser': True,
    },
    (errors.NotOwner,): {
        'name': 'Bot owner-only commands called',
        'key': 'NotOwner',
        'level': logging.WARNING,
        'superuser': True,
    },
    (extension.ModuleDisabled,): {
        'name': 'Disabled module called',
        'key': 'ModuleDisabled',
        'level': logging.INFO,
    },
    (constraint.ConstraintFailure,): {
        'name': 'Constraint violations',
        'key': 'ConstraintFailure',
        'level': logging.INFO,
    },
}

PRIVILEGED_EXCEPTIONS = {d['key'] for d in EXCEPTIONS.values() if d.get('superuser')}

COLORS = {
    logging.DEBUG: Color(0x6610f2),
    logging.INFO: Color(0x0d6efd),
    logging.WARNING: Color(0xffc107),
    logging.ERROR: Color(0xdc3545),
    logging.CRITICAL: Color(0xd63384),
}

_log = logging.getLogger('discord.logging.exceptions')


class ContextualLogger:
    def __init__(self, prefix: str, ctx: Circumstances):
        self.prefix = prefix
        self.ctx = ctx

    async def log(self, msg_class: str, level: int, msg: str, *args,
                  exc_info: Optional[BaseException] = None,
                  embed: Optional[Embed] = None, **kwargs):
        logger = logging.getLogger(f'{self.prefix}.{msg_class}')
        logger.log(level, unmarked(msg), *args, exc_info=exc_info, **kwargs)
        await self.deliver(msg_class, msg, embed, exc_info)

    def get_dest_info(self, msg_class: str) -> Tuple[TextChannel, str, Role | None]:
        config: _LoggingConf | None = self.ctx.log_config.get(msg_class)
        if not config:
            raise LookupError
        channel = config.get('channel')
        if not channel:
            raise LookupError
        channel: TextChannel = self.ctx.guild.get_channel(channel)
        if not isinstance(channel, TextChannel):
            raise LookupError
        role = config.get('role', None)
        if role:
            role: Role = self.ctx.guild.get_role(role)
        name = config.get('name', 'Logging')
        return channel, name, role

    async def deliver(self, msg_class: str, msg: str,
                      embed: Optional[Embed] = None,
                      exc_info: Optional[BaseException] = None):
        try:
            channel, name, role = self.get_dest_info(msg_class)
        except LookupError:
            return
        msg = f'**{escape_markdown(name)}**\n{msg}'
        if role:
            msg = f'{tag(role)}\n{msg}'
            mentions = AllowedMentions(roles=[role])
        else:
            mentions = AllowedMentions.none()

        await channel.send(content=msg, allowed_mentions=mentions, embed=embed)
        await report_exception(channel, exc_info)

    debug = partialmethod(log, level=logging.DEBUG)
    info = partialmethod(log, level=logging.INFO)
    warning = partialmethod(log, level=logging.WARNING)
    error = partialmethod(log, level=logging.ERROR)
    critical = partialmethod(log, level=logging.CRITICAL)


async def log_command_errors(ctx: Circumstances, exc: errors.CommandError):
    for types, info in EXCEPTIONS.items():
        if isinstance(exc, types):
            break
    else:
        _log.warning('Uncaught exception while handling command:\n'
                     f'{ctx.message.content}',
                     exc_info=exc)
        return
    if isinstance(exc, errors.CommandInvokeError):
        exc_info = exc.__cause__
    else:
        exc_info = None
    title = info['name']
    level = info['level']
    embed = Embed(
        title=title,
        description=str(exc),
        timestamp=utcnow(),
        url=ctx.message.jump_url,
        color=COLORS[level],
    )
    embed.add_field(name='Author', value=tag(ctx.author), inline=True)
    embed.add_field(name='Channel', value=tag(ctx.channel), inline=True)
    embed.add_field(name='Message', value=trunc_for_field(ctx.message.content), inline=False)
    return await ctx.log.log(info['key'], level, '', exc_info=exc_info, embed=embed)


def censor_paths(tb: str):
    for path in sys.path:
        tb = tb.replace(path, '')
    return tb


async def report_exception(channel: TextChannel, exc_info: BaseException):
    if not isinstance(exc_info, BaseException):
        return
    tb = traceback.format_exception(type(exc_info), exc_info, exc_info.__traceback__)
    tb_body = censor_paths(''.join(tb))
    tb_file = io.BytesIO(tb_body.encode())
    filename = f'stacktrace.{localnow().isoformat().replace(":", ".")}.py'
    await channel.send(file=File(tb_file, filename=filename))