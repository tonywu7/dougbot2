# utils.py
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

from datetime import datetime
from typing import List, Tuple
from urllib.parse import urlencode, urlunsplit

import attr
from aiohttp import ClientSession
from discord import Embed
from discord.utils import escape_markdown

from ...utils.markdown import a, strong, trunc_for_field


@attr.s
class OEISEntry:
    number: int = attr.ib()
    data: List[int] = attr.ib(converter=lambda s: [int(n) for n in s.split(',')])
    name: str = attr.ib()
    created: datetime = attr.ib(converter=datetime.fromisoformat)
    formula: List[str] = attr.ib()
    author: str = attr.ib(default='(none)')

    @classmethod
    def from_dict(cls, data) -> OEISEntry:
        keys = attr.fields_dict(cls).keys()
        return cls(**{k: data.get(k) for k in keys})

    @property
    def url(self) -> str:
        return f'https://oeis.org/A{self.number}'

    @property
    def title(self) -> str:
        return f'A{self.number:06} {escape_markdown(self.name)}'

    @property
    def description(self) -> str:
        return trunc_for_field(', '.join([str(n) for n in self.data]))

    def to_embed(self) -> Embed:
        embed = (Embed(title=self.title, description=self.description)
                 .add_field(name='Source', value=a(self.url, 'View on OEIS')))
        if self.author:
            embed.add_field(name='Author', value=self.author)
        # if self.formula:
        #     embed.add_field(name='Formula', value='\n'.join([code(f) for f in limit_results(self.formula, 3)]))
        embed.set_author(name='The On-Line Encyclopedia of Integer Sequences®',
                         icon_url='https://oeis.org/oeis_logo.png',
                         url=self.url).set_footer(text='Created')
        embed.timestamp = self.created
        return embed

    def to_text(self) -> str:
        return f'{strong(self.title)}\n{self.description}\n{self.url}'


class OEIS:
    def __init__(self, session: ClientSession):
        self.session = session

    def get_api_url(self, query: str) -> str:
        return urlunsplit(('https', 'oeis.org', 'search',
                           urlencode([('q', query), ('fmt', 'json')]), ''))

    async def get(self, query: str) -> Tuple[OEISEntry, int]:
        async with self.session.get(self.get_api_url(query)) as res:
            data = await res.json()
            count = data['count']
            if not count:
                raise ValueError('No result found.')
            results = data['results']
            if not results:
                raise ValueError('Too many results found for this query.')
            return OEISEntry.from_dict(results[0]), count
