# env.py
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

from contextvars import ContextVar

from discord.ext.commands import Context as CommandContext
from jinja2 import Environment, Template, select_autoescape

cctx: ContextVar[CommandContext] = ContextVar('cctx')


def get_environment():
    return Environment(
        loader=None, bytecode_cache=None,
        autoescape=select_autoescape(),
        enable_async=True,
    )


async def render(ctx: CommandContext, template: Template, variables: dict):
    cctx.set(ctx)
    return await template.render_async(**variables)
