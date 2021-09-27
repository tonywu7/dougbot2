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

# TODO: Rewrite as per-instance config

from __future__ import annotations

import io
import logging
import sys
import traceback
from functools import partialmethod
from typing import Optional, TypedDict

from discord import (AllowedMentions, Color, File, Forbidden, Guild, NotFound,
                     Role, TextChannel)
from discord.ext.commands import Context, errors
from discord.utils import escape_markdown
from duckcord.embeds import Embed2

from ...utils.datetime import localnow, utcnow
from ...utils.markdown import tag, unmarked, untagged
from ...utils.pagination import trunc_for_field


class _ErrorConf(TypedDict):
    exc: tuple[type[Exception], ...]
    name: str
    level: int
    superuser: Optional[bool]


UNCAUGHT_EXCEPTIONS = (
    errors.CommandInvokeError,
    errors.ArgumentParsingError,
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
    errors.UserInputError,
    errors.CheckFailure,
    errors.NoPrivateMessage,
    errors.PrivateMessageOnly,
    Forbidden,
    NotFound,
}


class LoggingEntry(TypedDict):
    """A configurable entry for logging.

    The channel and role attributes are to be set on the website.
    """
    name: str
    channel: int
    role: Optional[int]


LoggingConfig = dict[str, LoggingEntry]

_log = logging.getLogger('discord.logging.exceptions')


def get_name(key: str) -> str:
    """Get the displayed title for the logging config with this key."""
    return logging_classes[key]


def register_logger(key: str, name: str):
    """Add a logger."""
    if key in logging_classes:
        raise ValueError(
            f'A logger for {key} named "{logging_classes[key]}"'
            ' has already been defined.',
        )
    logging_classes[key] = name


class ServerLogger:
    """Per-guild logging dispatcher.

    Emulates the logging.Logger class. Each logging config map a logging class
    (c.f. `Logger` names) to a guild channel. The logger sends a message to
    the corresponding channel when the `log` method is called with the matching
    logging class.

    Other components of the bot can then simply log the message (optionally with
    embeds), and leave guild admins to decide whether (or if at all) they would
    like to receive that message.
    """

    def __init__(self, prefix: str, guild: Guild, config: LoggingConfig):
        self.prefix = prefix
        self.guild = guild
        self.config = config
        self._log = logging.getLogger('discord.logger')

    async def log(self, msg_class: str, level: int, msg: str, *args,
                  exc_info: Optional[BaseException] = None,
                  embed: Optional[Embed2] = None, embed_only=False, **kwargs):
        # TODO: deprecate embed_only
        """Log a message.

        :param msg_class: Class of this log message; the logger looks up
        the corresponding guild channel using this as a key
        :type msg_class: str
        :param level: The logging level to use; same semantics as the levels
        from the builtin `logging` module
        :type level: int
        :param msg: The message to log
        :type msg: str
        :param exc_info: Associated exception, if any, defaults to None;
        same semantics as the `exc_info` argument in the `logging` module:
        if this is present, a traceback will be sent with the log message
        :type exc_info: Optional[BaseException], optional
        :param embed: The embed to send, defaults to None
        :type embed: Optional[Embed2], optional
        """
        logger = logging.getLogger(f'{self.prefix}.{msg_class}')
        logger.log(level, unmarked(untagged(msg)), *args, exc_info=exc_info, **kwargs)
        if embed_only:
            msg = ''
        await self.deliver(msg_class, msg, embed, exc_info)

    def get_dest_info(self, msg_class: str) -> tuple[TextChannel, str, Role | None]:
        """Look up and return the guild channel and role for this message class."""
        try:
            config = self.config[msg_class]
        except AttributeError:
            raise LookupError
        channel = config['channel']
        channel: TextChannel = self.guild.get_channel(channel)
        if not isinstance(channel, TextChannel):
            raise LookupError
        role = config.get('role', None)
        if role:
            role: Role = self.guild.get_role(role)
        name = config.get('name', 'Logging')
        return channel, name, role

    async def deliver(self, msg_class: str, msg: str,
                      embed: Optional[Embed2] = None,
                      exc_info: Optional[BaseException] = None):
        """Send out the log message."""
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
            await channel.send(content=msg, allowed_mentions=mentions,
                               embed=embed, file=get_traceback(exc_info))
        except Exception as e:
            self._log.error(f'Error while delivering logs: {e}', exc_info=e)

    debug = partialmethod(log, level=logging.DEBUG)
    info = partialmethod(log, level=logging.INFO)
    warning = partialmethod(log, level=logging.WARNING)
    error = partialmethod(log, level=logging.ERROR)
    critical = partialmethod(log, level=logging.CRITICAL)


def unpack_exc(exc: BaseException) -> BaseException:
    """Get the original exception.

    Checks the `original` attribute (for discord.py), then the `__cause__` attribute;
    returns the original exception if neither exists.
    """
    return getattr(exc, 'original', None) or exc.__cause__ or exc


def format_exception(exc: BaseException, title: Optional[str] = None,
                     color: Optional[Color] = Color.red()) -> Embed2:
    """Format the embed for exception details."""
    return Embed2(title=title or type(exc).__name__,
                  description=escape_markdown(str(exc), as_needed=True),
                  color=color, timestamp=utcnow())


def get_traceback(exc: BaseException) -> File:
    """Extract the stacktrace from an exception to a discord.File.

    All paths in `sys.path` will be removed from the stacktrace.
    """
    if not isinstance(exc, BaseException):
        return
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_body = censor_paths(''.join(tb))
    tb_file = io.BytesIO(tb_body.encode())
    filename = f'stacktrace.{localnow().isoformat().replace(":", ".")}.py'
    return File(tb_file, filename=filename)


async def log_command_error(ctx: Context, config: LoggingConfig, exc: errors.CommandError):
    """Log an exception thrown during the processing of this Context."""
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
        exc_info = unpack_exc(exc)
    else:
        exc_info = None
    if isinstance(exc_info, tuple(bypassed)):
        return
    title = conf['name']
    level = conf['level']
    embed = (format_exception(exc, title, COLORS[level])
             .add_field(name='Author', value=tag(ctx.author))
             .add_field(name='Channel', value=tag(ctx.channel))
             .add_field(name='Message', value=trunc_for_field(ctx.message.content), inline=False)
             .set_url(ctx.message.jump_url))
    msg = (f'Error while processing trigger {ctx.invoked_with}: '
           f'{type(exc).__name__}: {exc}')
    logger = ServerLogger('discord.exception', ctx.guild, config)
    return await logger.log(key, level, msg, exc_info=exc_info, embed=embed, embed_only=True)


def censor_paths(tb: str):
    """Remove all paths present in `sys.path` from the string."""
    for path in sys.path:
        tb = tb.replace(path, '')
    return tb
