# webservices.py
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

import random
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import urlencode, urlunsplit

import aiohttp
import attr
from aiohttp import ClientSession
from discord.ext.commands import BucketType, Greedy, command
from discord.utils import escape_markdown

from dougbot2.context import Circumstances
from dougbot2.exts import autodoc as doc
from dougbot2.utils import english
from dougbot2.utils.common import Embed2, a, can_embed, strong, trunc_for_field
from dougbot2.utils.converters import RegExp


@attr.s
class OEISEntry:
    number: int = attr.ib()
    data: list[int] = attr.ib(converter=lambda s: [int(n) for n in s.split(',')])
    name: str = attr.ib()
    created: datetime = attr.ib(converter=datetime.fromisoformat)
    formula: list[str] = attr.ib()
    author: str = attr.ib(default='(none)')

    @classmethod
    def from_dict(cls, data):
        keys = attr.fields_dict(cls).keys()
        return cls(**{k: data.get(k) for k in keys})

    @property
    def url(self) -> str:
        return f'https://oeis.org/A{self.number}'

    @property
    def title(self) -> str:
        return f'A{self.number:06} {trunc_for_field(escape_markdown(self.name), 248)}'

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


class WebServiceCommands:
    """Commands (mixin) for accessing the internet."""

    @command('oeis')
    @doc.description('Lookup a sequence from [OEIS](https://oeis.org/) '
                     'by its integers or by its A-number.')
    @doc.argument('integers', 'The sequence of integers to lookup, separated by space only.')
    @doc.argument('a_number', 'The OEIS A-number to lookup.')
    @doc.invocation((), 'Get a sequence by searching for a random A-number (may not return results).')
    @doc.invocation(('integers',), 'Find a sequence matching these numbers.')
    @doc.invocation(('a_number',), 'Find the exact sequence with this A-number.')
    @doc.invocation(('integers', 'a_number'), False)
    @doc.example('1 1 2 3 5 8', 'Find the Fibonacci numbers.')
    @doc.example('A018226', 'Find the magic numbers.')
    @doc.cooldown(1, 10, BucketType.guild)
    @doc.concurrent(1, BucketType.guild)
    @can_embed
    async def oeis(self, ctx: Circumstances, integers: Greedy[int],
                   a_number: Optional[RegExp[Literal[r'[Aa]\d+', 'A-number', 'such as A0000045']]] = None):
        """Get a result from OEIS."""
        if integers:
            if len(integers) == 1:
                query = f'A{integers[0]}'
            else:
                query = ' '.join([str(n) for n in integers])
        elif a_number:
            query = a_number[0]
        else:
            query = None

        async with ctx.typing():
            try:
                oeis = OEIS(ctx.request)
                if query:
                    sequence, num_results = await oeis.get(query)
                else:
                    sequence, num_results = await oeis.random()
            except ValueError as e:
                reason = str(e)
                if not integers and not a_number:
                    reason = f'{reason} (Searched for a random A-number {query})'
                return await ctx.response(ctx, content=reason).autodelete(20).run()
            except aiohttp.ClientError:
                await ctx.reply('Network error while searching on OEIS')
                raise

        async def more_result(*args, **kwargs):
            await ctx.send(f'({num_results - 1} more {english.pluralize(num_results - 1, "result")})')

        await (ctx.response(ctx, embed=sequence.to_embed())
               .callback(more_result).deleter().run(thread=True))
