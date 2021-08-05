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
from typing import Optional, TypedDict

from discord import AllowedMentions, Color, File, Role, TextChannel
from discord.ext.commands import Context, errors
from discord.utils import escape_markdown

from ts2.utils.datetime import localnow, utcnow

from ...utils.duckcord.embeds import Embed2
from ...utils.markdown import tag, unmarked, untagged
from ...utils.pagination import trunc_for_field


class _ErrorConf(TypedDict):
    exc: tuple[type[Exception], ...]
    name: str
    level: int
    superuser: Optional[bool]


UNCAUGHT_EXCEPTIONS = (
    errors.CommandInvokeError,
    errors.ConversionError,
    errors.ExtensionError,
    errors.ClientException,
)

EXCEPTIONS = {
    (errors.MaxConcurrencyReached,
     errors.CommandOnCooldown): {
        'name': 'Command throttling triggered',
        'key': 'CommandThrottling',
        'level': logging.DEBUG,
    },
    (errors.BotMissingAnyRole,
     errors.BotMissingPermissions,
     errors.BotMissingRole): {
        'name': 'Bot has insufficient permissions',
        'key': 'Unauthorized',
        'level': logging.WARNING,
    },
    (errors.MissingPermissions,
     errors.MissingAnyRole,
     errors.MissingRole): {
        'name': 'Member has insufficient permissions',
        'key': 'MissingPerms',
        'level': logging.DEBUG,
    },
    UNCAUGHT_EXCEPTIONS: {
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
}

COLORS = {
    logging.DEBUG: Color(0x6610f2),
    logging.INFO: Color(0x0d6efd),
    logging.WARNING: Color(0xffc107),
    logging.ERROR: Color(0xdc3545),
    logging.CRITICAL: Color(0xd63384),
}

exceptions: dict[str, _ErrorConf] = {v['key']: {'exc': k, **v} for k, v in EXCEPTIONS.items()}
privileged = {k for k, v in exceptions.items() if v.get('superuser')}
logging_classes: dict[str, str] = {k: v['name'] for k, v in exceptions.items()}
bypassed = {
    errors.CommandNotFound,
    errors.ArgumentParsingError,
    errors.UserInputError,
    errors.CheckFailure,
    errors.NoPrivateMessage,
    errors.PrivateMessageOnly,
}


class LoggingEntry(TypedDict):
    name: str
    channel: int
    role: Optional[int]


LoggingConfig = dict[str, LoggingEntry]

_log = logging.getLogger('discord.logging.exceptions')


def get_name(key: str) -> str:
    return logging_classes[key]


def register_logger(key: str, name: str):
    if key in logging_classes:
        raise ValueError(
            f'A logger for {key} named "{logging_classes[key]}"'
            ' has already been defined.',
        )
    logging_classes[key] = name


class ContextualLogger:
    def __init__(self, prefix: str, ctx: Context, config: LoggingConfig):
        self.prefix = prefix
        self.ctx = ctx
        self.config = config
        self._log = logging.getLogger('discord.logger')

    async def log(self, msg_class: str, level: int, msg: str, *args,
                  exc_info: Optional[BaseException] = None,
                  embed: Optional[Embed2] = None, embed_only=False, **kwargs):
        logger = logging.getLogger(f'{self.prefix}.{msg_class}')
        logger.log(level, unmarked(untagged(msg)), *args, exc_info=exc_info, **kwargs)
        if embed_only:
            msg = ''
        await self.deliver(msg_class, msg, embed, exc_info)

    def get_dest_info(self, msg_class: str) -> tuple[TextChannel, str, Role | None]:
        try:
            config = self.config[msg_class]
        except AttributeError:
            raise LookupError
        channel = config['channel']
        channel: TextChannel = self.ctx.guild.get_channel(channel)
        if not isinstance(channel, TextChannel):
            raise LookupError
        role = config.get('role', None)
        if role:
            role: Role = self.ctx.guild.get_role(role)
        name = config.get('name', 'Logging')
        return channel, name, role

    async def deliver(self, msg_class: str, msg: str,
                      embed: Optional[Embed2] = None,
                      exc_info: Optional[BaseException] = None):
        try:
            channel, name, role = self.get_dest_info(msg_class)
        except LookupError:
            return
        msg = f'**{escape_markdown(name)}**\n{msg}'
        mentions = AllowedMentions.none()
        if role:
            msg = f'{tag(role)}\n{msg}'
            if len(role.members) <= 25:
                mentions = AllowedMentions(roles=[role])

        try:
            await channel.send(content=msg, allowed_mentions=mentions, embed=embed)
            await report_exception(channel, exc_info)
        except Exception as e:
            self._log.error(f'Error while delivering logs: {e}', exc_info=e)

    debug = partialmethod(log, level=logging.DEBUG)
    info = partialmethod(log, level=logging.INFO)
    warning = partialmethod(log, level=logging.WARNING)
    error = partialmethod(log, level=logging.ERROR)
    critical = partialmethod(log, level=logging.CRITICAL)


def format_exception(exc: BaseException, title: Optional[str] = None,
                     color: Optional[Color] = Color.red()) -> Embed2:
    return Embed2(title=title or type(exc).__name__,
                  description=str(exc), color=color,
                  timestamp=utcnow())


def get_traceback(exc: BaseException) -> File:
    if not isinstance(exc, BaseException):
        return
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_body = censor_paths(''.join(tb))
    tb_file = io.BytesIO(tb_body.encode())
    filename = f'stacktrace.{localnow().isoformat().replace(":", ".")}.py'
    return File(tb_file, filename=filename)


async def log_command_errors(ctx: Context, config: LoggingConfig, exc: errors.CommandError):
    if isinstance(exc, tuple(bypassed)):
        return
    for key, conf in exceptions.items():
        if isinstance(exc, conf['exc']):
            break
    else:
        _log.warning('Uncaught exception while handling command:\n'
                     f'{ctx.message.content}',
                     exc_info=exc)
        return
    if isinstance(exc, UNCAUGHT_EXCEPTIONS):
        exc_info = exc.__cause__
    else:
        exc_info = None
    title = conf['name']
    level = conf['level']
    embed = (format_exception(exc, title, COLORS[level])
             .add_field(name='Author', value=tag(ctx.author))
             .add_field(name='Channel', value=tag(ctx.channel))
             .add_field(name='Message', value=trunc_for_field(ctx.message.content), inline=False)
             .set_url(ctx.message.jump_url))
    msg = (f'Error while processing trigger {ctx.invoked_with}: '
           f'{type(exc).__name__}: {exc}')
    logger = ContextualLogger('discord.exception', ctx, config)
    return await logger.log(key, level, msg, exc_info=exc_info, embed=embed, embed_only=True)


def censor_paths(tb: str):
    for path in sys.path:
        tb = tb.replace(path, '')
    return tb


async def report_exception(channel: TextChannel, exc_info: BaseException):
    await channel.send(file=get_traceback(exc_info))
