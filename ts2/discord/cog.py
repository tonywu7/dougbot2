# extension.py
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

import logging

from discord.ext.commands import Bot, Cog, CogMeta, Context
from discord.ext.commands.errors import DisabledCommand
from django.apps import apps

from .config import CommandAppConfig


class GearMeta(CogMeta):
    def __new__(cls, *args, order: int = 50, **kwargs):
        new_cls = super().__new__(cls, *args, **kwargs)
        new_cls.sort_order = order
        return new_cls


class Gear(Cog, metaclass=GearMeta):
    def __init__(self, label: str, bot: Bot, *args, **kwargs):
        from .bot import Robot
        super().__init__()
        self.bot: Robot = bot
        self.app_label = label
        self.log = logging.getLogger(f'discord.logging.ext.{label}')


async def cog_enabled_check(ctx: Context) -> bool:
    from .models import Server
    if await ctx.bot.is_owner(ctx.author):
        return True
    try:
        server: Server = ctx.server
    except AttributeError:
        return True
    extension: Gear = ctx.cog
    if not isinstance(extension, Gear):
        return True
    if extension.app_label in server.extensions:
        return True
    conf: CommandAppConfig = apps.get_app_config(extension.app_label)
    if conf.hidden:
        return True
    raise ModuleDisabled(extension)


class ModuleDisabled(DisabledCommand):
    def __init__(self, cog: Cog, *args):
        self.module = cog.qualified_name
        super().__init__(message=f'Attempted to use disabled module {cog.qualified_name}', *args)
