# errors.py
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

import io
import logging
import sys
import traceback
from typing import Dict, Optional, Tuple, Type, TypedDict

from discord import Color, Embed, File, TextChannel
from discord.ext.commands import errors

from telescope2.utils.datetime import localnow, utcnow

from . import constraint, extension
from .context import Circumstances
from .utils.textutil import tag, trunc_for_field


class _ErrorConf(TypedDict):
    name: str
    key: str
    level: int
    superuser: Optional[bool]


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

COLORS = {
    logging.DEBUG: Color(0xc774df),
    logging.INFO: Color(0xd3d3d3),
    logging.WARNING: Color(0xd29a61),
    logging.ERROR: Color(0xe26a72),
    logging.CRITICAL: Color(0xe26a72),
}

PRIVILEGED_EXCEPTIONS = {d['key'] for d in EXCEPTIONS.values() if d.get('superuser')}


async def log_command_errors(ctx: Circumstances, exc: errors.CommandError):
    for types, info in EXCEPTIONS.items():
        if isinstance(exc, types):
            break
    else:
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
