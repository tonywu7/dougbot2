# __init__.py
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

# TODO: Move to respective cogs

from discord.ext.commands import CommandError

from ...ext.autodoc import explains


class ServiceUnavailable(CommandError):
    def __init__(self, message='', *args):
        super().__init__(message=message, *args)


@explains(ServiceUnavailable, 'Temporarily unavailable', 10)
async def explains_bad_invite(ctx, exc: ServiceUnavailable) -> tuple[str, int]:
    return f'{exc}\nPlease try again later.', 20
