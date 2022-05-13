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
from dataclasses import dataclass
from functools import partial, partialmethod
from typing import Optional, Union, overload

from discord import AllowedMentions, Color, File, Guild, Role, TextChannel
from discord.ext.commands import Context
from discord.utils import escape_markdown

from ...blueprints import Console, LoggingAmenities
from ...utils.async_ import async_get
from ...utils.datastructures import TypeDictionary
from ...utils.datetime import localnow, utcnow
from ...utils.duckcord.embeds import Embed2
from ...utils.markdown import tag, unmarked, untagged
from ...utils.pagination import trunc_for_field

COLORS = {
    logging.DEBUG: Color(0x6610F2),
    logging.INFO: Color(0x0D6EFD),
    logging.WARNING: Color(0xFFC107),
    logging.ERROR: Color(0xDC3545),
    logging.CRITICAL: Color(0xD63384),
}


@dataclass
class LoggerSpec:
    name: str
    title: str
    level: int = logging.INFO
    stack: bool = False

    @property
    def color(self) -> Color:
        return COLORS[self.level]


class Papertrail(LoggingAmenities):
    def __init__(self):
        self._loggers: dict[str, LoggerSpec] = {}
        self._errors: TypeDictionary[
            type[Exception], Union[str, bool]
        ] = TypeDictionary()

    def register_logger(
        self,
        name: str,
        *exc_classes: type[Exception],
        title: Optional[str] = None,
        level: int = logging.INFO,
        show_stacktrace: bool = False,
    ):
        self._loggers[name] = LoggerSpec(name, title or name, level, show_stacktrace)
        self._errors[exc_classes] = name

    def ignore_exception(self, *exc: type[Exception]):
        self._errors[exc] = False

    @overload
    def get_logger(self, name: str) -> ServerLogger:
        ...

    @overload
    def get_loader(self, name: str, guild: Guild) -> BoundServerLogger:
        ...

    def get_logger(self, name: str, guild: Optional[Guild] = None):
        spec = self._loggers.get(name, LoggerSpec(name, name))
        if guild is None:
            return ServerLogger(spec)
        return BoundServerLogger(guild, spec)

    def dump_traceback(self, exc: BaseException) -> File:
        return _get_traceback(exc)

    def pprint_exception(
        self, exc: Exception, color: Color = Color(0), title: Optional[str] = None
    ) -> Embed2:
        return _get_exception_embed(exc, color, title)

    async def log_exception(self, ctx: Context, exc: Exception) -> None:
        exc_type = type(exc)
        if not (logger_name := self._errors.get(exc_type)):
            return
        spec = self._loggers[logger_name]
        if spec.stack:
            exc_info = _unpack_exc(exc)
        else:
            exc_info = None
        embed = (
            _get_exception_embed(exc, spec.color, spec.title)
            .add_field(name="Author", value=tag(ctx.author))
            .add_field(name="Channel", value=tag(ctx.channel))
            .add_field(
                name="Message", value=trunc_for_field(ctx.message.content), inline=False
            )
            .set_url(ctx.message.jump_url)
        )
        msg = (
            f"Error while processing trigger {ctx.invoked_with}: "
            f"{type(exc).__name__}: {exc}"
        )
        logger = self.get_logger(logger_name)
        await logger.log(ctx.guild, spec.level, msg, exc_info=exc_info, embed=embed)


class ServerLogger:
    """Logging dispatcher for servers.

    Emulates logging.Logger. Each logging config map a logging class
    (c.f. `Logger` names) to a guild channel. The logger sends a message to
    the corresponding channel when the `log` method is called with the matching
    logging class.

    Other components of the bot can then simply log the message (optionally with
    embeds), and leave guild admins to decide whether (or if at all) they would
    like to receive that message.
    """

    def __init__(self, spec: LoggerSpec):
        self.spec = spec
        self.logger = logging.getLogger(f"discord.logging.{spec.name}")

    async def log(
        self,
        guild: Optional[Guild],
        level: int,
        msg: str,
        *args,
        exc_info: Optional[BaseException] = None,
        embed: Optional[Embed2] = None,
        **kwargs,
    ):
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
        self.logger.log(
            level, unmarked(untagged(msg)), *args, exc_info=exc_info, **kwargs
        )
        if guild is None:
            return
        try:
            channel, role = await self.get_dest_info(guild)
        except LookupError:
            return
        msg = f"**{escape_markdown(self.spec.title)}**\n{msg}"
        mentions = AllowedMentions.none()
        if role:
            msg = f"{tag(role)}\n{msg}"
            if len(role.members) <= 25:
                mentions = AllowedMentions(roles=[role])

        try:
            await channel.send(
                content=msg,
                allowed_mentions=mentions,
                embed=embed,
                file=_get_traceback(exc_info),
            )
        except Exception as e:
            self.logger.error(f"Error while delivering logs: {e}", exc_info=e)

    async def get_dest_info(self, guild: Guild) -> tuple[TextChannel, Optional[Role]]:
        """Look up and return the guild channel and role for this message class."""
        from .models import LoggingChannel

        try:
            target: LoggingChannel = await async_get(
                LoggingChannel, key=self.spec.name, guild_id=guild.id
            )
        except LoggingChannel.DoesNotExist:
            raise LookupError
        channel: TextChannel = guild.get_channel(target.channel_id)
        if not isinstance(channel, TextChannel):
            raise LookupError
        if target.role_id:
            role: Role = guild.get_role(target.role_id)
        return channel, role

    debug = partialmethod(log, level=logging.DEBUG)
    info = partialmethod(log, level=logging.INFO)
    warning = partialmethod(log, level=logging.WARNING)
    error = partialmethod(log, level=logging.ERROR)
    critical = partialmethod(log, level=logging.CRITICAL)


class BoundServerLogger(ServerLogger, Console):
    def __init__(self, guild: Guild, spec: LoggerSpec):
        super().__init__(spec)
        self.log = partial(self.log, guild=guild)
        self.debug = partial(self.debug, guild=guild)
        self.info = partial(self.info, guild=guild)
        self.warning = partial(self.warning, guild=guild)
        self.error = partial(self.error, guild=guild)
        self.critical = partial(self.critical, guild=guild)


def _unpack_exc(exc: BaseException) -> BaseException:
    """Get the original exception.

    Checks the `original` attribute (for discord.py), then the `__cause__` attribute;
    returns the original exception if neither exists.
    """
    return getattr(exc, "original", None) or exc.__cause__ or exc


def _get_traceback(exc: BaseException) -> File:
    """Extract the stacktrace from an exception to a discord.File.

    All paths in `sys.path` will be removed from the stacktrace.
    """
    if not isinstance(exc, BaseException):
        return
    tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
    tb_body = _censor_paths("".join(tb))
    tb_file = io.BytesIO(tb_body.encode())
    filename = f'stacktrace.{localnow().isoformat().replace(":", ".")}.py'
    return File(tb_file, filename=filename)


def _censor_paths(tb: str):
    """Remove all paths present in `sys.path` from the string."""
    for path in sys.path:
        tb = tb.replace(path, "")
    return tb


def _get_exception_embed(exc: Exception, color: Color = Color(0), title=None):
    return Embed2(
        title=title or type(exc).__name__,
        description=escape_markdown(str(exc), as_needed=True),
        color=color,
        timestamp=utcnow(),
    )
