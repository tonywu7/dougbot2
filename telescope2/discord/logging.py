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

import logging
from functools import partialmethod
from typing import List, Optional, Tuple, TypedDict

from discord import AllowedMentions, Embed, Role, TextChannel
from discord.utils import escape_markdown

from telescope2.utils.discord import tag, unmarked

from .context import Circumstances
from .errors import report_exception


class _LoggingConf(TypedDict):
    key: str
    name: str
    channel: int
    role: Optional[int]


LOGGING_CLASSES: List[_LoggingConf] = []


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
