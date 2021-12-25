# environment.py
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

from discord import AllowedMentions, Color, File, Guild, Role, TextChannel
from discord.ext.commands import Context
from discord.utils import escape_markdown
from duckcord.embeds import Embed2

from ...utils.async_ import async_get
from ...utils.datastructures import TypeDictionary
from ...utils.datetime import localnow, utcnow
from ...utils.markdown import tag, unmarked, untagged
from ...utils.pagination import trunc_for_field
from .models import LoggingChannel

COLORS = {
    logging.DEBUG: Color(0x6610f2),
    logging.INFO: Color(0x0d6efd),
    logging.WARNING: Color(0xffc107),
    logging.ERROR: Color(0xdc3545),
    logging.CRITICAL: Color(0xd63384),
}


class LoggingParams(TypedDict):
    title: str
    level: int
    stack: Optional[bool]


class Environment:
    def __init__(self):
        self.loggers: dict[str, LoggingParams] = {}
        self.errors: TypeDictionary[type[Exception], str] = TypeDictionary()

    def add_logger(self, name: str, *exc_classes: type[Exception],
                   title: str, level: int, stack=False):
        self.loggers[name] = {
            'title': title,
            'level': level,
            'stack': stack,
        }
        for exc in exc_classes:
            self.errors[exc] = name

    def ignore_exception(self, exc: type[Exception]):
        self.errors[exc] = False

    def get_logger(self, name: str) -> ServerLogger:
        return ServerLogger(self, name, self.get_title(name))

    def get_title(self, name: str) -> int:
        return self.loggers[name]['title']

    def get_color(self, name: str) -> Color:
        return COLORS[self.loggers[name]['level']]

    def merge(self, *envs: Environment):
        for env in envs:
            self.loggers.update(env.loggers)
            self.errors._dict.update(env.errors._dict)

    def iter_params(self, stack_enabled=False):
        for name, logger in self.loggers.items():
            if not logger.get('stack') or stack_enabled:
                yield {**logger, 'key': name}

    def stacktrace_enabled(self, key: str):
        return self.loggers[key].get('stack')


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

    def __init__(self, env: Environment, name: str, title: str):
        self.env = env
        self.name = name
        self.title = title
        self.logger = logging.getLogger(f'discord.logging.{name}')

    async def log(self, guild: Guild, level: int, msg: str, *args,
                  exc_info: Optional[BaseException] = None,
                  embed: Optional[Embed2] = None, **kwargs):
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
        self.logger.log(level, unmarked(untagged(msg)), *args, exc_info=exc_info, **kwargs)

        try:
            channel, role = await self.get_dest_info(guild)
        except LookupError:
            return
        msg = f'**{escape_markdown(self.title)}**\n{msg}'
        mentions = AllowedMentions.none()
        if role:
            msg = f'{tag(role)}\n{msg}'
            if len(role.members) <= 25:
                mentions = AllowedMentions(roles=[role])

        try:
            await channel.send(content=msg, allowed_mentions=mentions,
                               embed=embed, file=get_traceback(exc_info))
        except Exception as e:
            self.logger.error(f'Error while delivering logs: {e}', exc_info=e)

    async def get_dest_info(self, guild: Guild) -> tuple[TextChannel, Optional[Role]]:
        """Look up and return the guild channel and role for this message class."""
        try:
            target: LoggingChannel = await async_get(LoggingChannel, key=self.name, server_id=guild.id)
        except LoggingChannel.DoesNotExist:
            raise LookupError
        channel: TextChannel = self.guild.get_channel(target.channel_id)
        if not isinstance(channel, TextChannel):
            raise LookupError
        if target.role:
            role: Role = self.guild.get_role(target.role)
        return channel, role

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


def censor_paths(tb: str):
    """Remove all paths present in `sys.path` from the string."""
    for path in sys.path:
        tb = tb.replace(path, '')
    return tb


def get_exception_embed(exc: Exception, color: Color = Color(0), title=None):
    return Embed2(title=title or type(exc).__name__,
                  description=escape_markdown(str(exc), as_needed=True),
                  color=color, timestamp=utcnow())


async def log_exception(env: Environment, ctx: Context, exc: Exception):
    exc_type = type(exc)
    if not (logger_name := env.errors.get(exc_type)):
        return
    params = env.loggers[logger_name]
    title = params['title']
    level = params['level']
    if params.get('stack'):
        exc_info = unpack_exc(exc)
    else:
        exc_info = None
    embed = (
        get_exception_embed(exc, env.get_color(logger_name), title)
        .add_field(name='Author', value=tag(ctx.author))
        .add_field(name='Channel', value=tag(ctx.channel))
        .add_field(name='Message', value=trunc_for_field(ctx.message.content), inline=False)
        .set_url(ctx.message.jump_url)
    )
    msg = (f'Error while processing trigger {ctx.invoked_with}: '
           f'{type(exc).__name__}: {exc}')
    logger = env.get_logger(logger_name)
    return await logger.log(ctx.guild, level, msg, exc_info=exc_info, embed=embed)
