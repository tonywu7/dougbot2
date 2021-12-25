# geography.py
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

from discord.ext.commands import BadArgument, Converter

from ..markdown import verbatim
from ..osm import parse_point_no_warning


class Latitude(Converter):
    """Convert a string to a float representing a latitude.

    Accepts a regular floating-point number and the degree-minute-second notation.
    Ensures the number is within a valid range (-90 to 90).
    """

    def __init__(self) -> None:
        pass

    async def convert(self, ctx, argument: str) -> float:
        try:
            point = parse_point_no_warning(f'{argument} 0')
            return point.latitude
        except ValueError:
            raise BadArgument(f'Failed to parse {verbatim(argument)} as a latitude')


class Longitude(Converter):
    """Convert a string to a float representing a latitude.

    Accepts a regular floating-point number and the degree-minute-second notation.
    Ensures the number is within a valid range (0 to 180).
    """

    def __init__(self) -> None:
        pass

    async def convert(self, ctx, argument: str) -> float:
        try:
            point = parse_point_no_warning(f'0 {argument}')
            return point.longitude
        except ValueError:
            raise BadArgument(f'Failed to parse {verbatim(argument)} as a longitude')
