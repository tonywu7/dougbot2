# apps.py
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

from contextlib import suppress

from discord.ext.commands import Bot
from django.apps import AppConfig

from ...utils.importutil import get_submodule_from_apps
from .defaults import default_env
from .environment import Environment


class AutodocConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ts2.discord.exts.autodoc'
    default = True


def setup(bot: Bot):
    env = default_env()
    envs = []
    for app, module in get_submodule_from_apps('autodoc'):
        with suppress(AttributeError):
            envs.append(Environment(module.setup_docs(bot)))
    env.merge(*envs)
    env.init_bot(bot)
    bot.doc_env = env
