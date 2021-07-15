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
from collections.abc import Iterator
from functools import partialmethod
from typing import Optional, TypedDict

from discord import AllowedMentions, Color, Embed, File, Role, TextChannel
from discord.ext.commands import Context, errors
from discord.utils import escape_markdown

from ts2.utils.datetime import localnow, utcnow

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
        'name': 'Command throttling hit',
        'key': 'CommandThrottling',
        'level': logging.DEBUG,
    },
    (errors.BotMissingAnyRole,
     errors.BotMissingPermissions,
     errors.BotMissingRole): {
        'name': 'Bot permission requirements not met',
        'key': 'Unauthorized',
        'level': logging.WARNING,
    },
    (errors.MissingPermissions,
     errors.MissingAnyRole,
     errors.MissingRole): {
        'name': 'Unauthorized invocations',
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
}


class LoggingEntry(TypedDict):
    name: str
    channel: int
    role: Optional[int]


LoggingConfig = dict[str, LoggingEntry]

_log = logging.getLogger('discord.logging.exceptions')


def can_change(user, key: str) -> bool:
    return (key not in privileged or user.is_superuser)  # Material conditional


def iter_logging_conf(user) -> Iterator[tuple[str, _ErrorConf]]:
    for k, v in exceptions.items():
        if can_change(user, k):
            yield k, v
    for k in logging_classes.keys() - exceptions.keys():
        yield k, {'name': logging_classes[k]}


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
    def __init__(self, prefix: str, ctx: Context):
        self.prefix = prefix
        self.ctx = ctx

    async def log(self, msg_class: str, level: int, msg: str, *args,
                  exc_info: Optional[BaseException] = None,
                  embed: Optional[Embed] = None, embed_only=False, **kwargs):
        logger = logging.getLogger(f'{self.prefix}.{msg_class}')
        logger.log(level, unmarked(untagged(msg)), *args, exc_info=exc_info, **kwargs)
        if embed_only:
            msg = ''
        await self.deliver(msg_class, msg, embed, exc_info)

    def get_dest_info(self, msg_class: str) -> tuple[TextChannel, str, Role | None]:
        config: LoggingConfig = self.ctx.log_config[msg_class]
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


async def log_command_errors(ctx: Context, exc: errors.CommandError):
    if isinstance(exc, tuple(bypassed)):
        return
    for conf in exceptions.values():
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
    msg = (f'Error while processing trigger {ctx.invoked_with}: '
           f'{type(exc).__name__}: {exc}')
    logger = ContextualLogger('discord.exception', ctx)
    print(conf)
    return await logger.log(conf['key'], level, msg, exc_info=exc_info, embed=embed, embed_only=True)


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
