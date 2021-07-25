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

import random
from datetime import datetime
from urllib.parse import urlencode, urlunsplit

import attr
from aiohttp import ClientSession
from discord.utils import escape_markdown

from ts2.discord.utils.markdown import a, strong
from ts2.discord.utils.pagination import Embed2, trunc_for_field


@attr.s
class OEISEntry:
    number: int = attr.ib()
    data: list[int] = attr.ib(converter=lambda s: [int(n) for n in s.split(',')])
    name: str = attr.ib()
    created: datetime = attr.ib(converter=datetime.fromisoformat)
    formula: list[str] = attr.ib()
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

    def to_embed(self) -> Embed2:
        embed = (
            Embed2(title=self.title, description=self.description, timestamp=self.created)
            .add_field(name='Source', value=a('View on OEIS', self.url))
            .set_author(name='The On-Line Encyclopedia of Integer Sequences®',
                        icon_url='https://oeis.org/oeis_logo.png',
                        url=self.url)
            .set_footer(text='Created')
        )
        if self.author:
            embed = embed.add_field(name='Author', value=self.author)
        return embed

    def to_text(self) -> str:
        return f'{strong(self.title)}\n{self.description}\n{self.url}'


class OEIS:
    NUM_SEQUENCES = 341962  # 21 Jun 2021

    def __init__(self, session: ClientSession):
        self.session = session

    def get_api_url(self, query: str) -> str:
        return urlunsplit(('https', 'oeis.org', 'search',
                           urlencode([('q', query), ('fmt', 'json')]), ''))

    async def get(self, query: str) -> tuple[OEISEntry, int]:
        async with self.session.get(self.get_api_url(query)) as res:
            data = await res.json()
            count = data['count']
            if not count:
                raise ValueError('No result found.')
            results = data['results']
            if not results:
                raise ValueError('Too many results found for this query.')
            return OEISEntry.from_dict(results[0]), count

    async def random(self) -> tuple[OEISEntry, int]:
        return await self.get(f'A{random.randrange(1, self.NUM_SEQUENCES)}')
