# command.py
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

from functools import wraps

from discord.ext.commands import Context


def on_error_reset_cooldown(f):
    """Wrap a command callback such that command cooldowns are reset if the command raises."""

    @wraps(f)
    async def wrapper(*args, **kwargs):
        try:
            return await f(*args, **kwargs)
        except Exception:
            if isinstance(args[0], Context):
                ctx = args[0]
            else:
                ctx = args[1]
            ctx.command.reset_cooldown(ctx)
            raise

    return wrapper
