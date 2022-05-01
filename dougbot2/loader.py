# loader.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

import os
from inspect import Parameter

from discord.ext.commands import Context

from . import exceptions as exc
from .blueprints import MissionControl, Surroundings
from .defaults import get_defaults


def _arg_delimiter(idx: int, param: Parameter):
    if idx == 0:
        return 'skip'
    if (
        param.annotation is Surroundings
        or isinstance(param.annotation, type)
        and issubclass(param.annotation, Context)
    ):
        return 'skip'
    if param.kind is Parameter.VAR_KEYWORD:
        return 'break'
    return 'proceed'


def setup(bot: MissionControl):
    bot.manpage.set_arg_delimiter(_arg_delimiter)

    err = bot.errorpage

    err.set_error_blurb(exc.NotAcceptable, err.exception_to_str)
    err.set_error_blurb(
        exc.ServiceUnavailable,
        lambda ctx, exc: f'{exc}\nPlease try again later.',
    )
    err.set_error_blurb(exc.DirectMessageForbidden, err.exception_to_str)

    err.add_error_fluff(exc.NotAcceptable, 'Bad input')
    err.add_error_fluff(exc.ServiceUnavailable, 'Temporarily unavailable')
    err.add_error_fluff(exc.DirectMessageForbidden, 'Direct message forbidden')

    os.environ['NLTK_DATA'] = get_defaults().default.nltk_data
