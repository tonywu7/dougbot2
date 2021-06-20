# bot.py
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
from typing import Literal, Optional

import aiohttp
from discord.ext.commands import BucketType, Greedy

from telescope2.utils.lang import pluralize

from ... import documentation as doc
from ...command import ensemble
from ...context import Circumstances
from ...converters import RegExp
from ...extension import Gear
from .utils import OEIS


class Internet(Gear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @ensemble('internet', aliases=['web', 'g'])
    @doc.description('Not Google.')
    @doc.invocation((), 'List all available sources.')
    async def internet(self, ctx: Circumstances):
        if not ctx.invoked_subcommand:
            await ctx.send_help()

    @internet.instruction('oeis')
    @doc.description('Lookup a sequence from [OEIS](https://oeis.org/) '
                     'by its integers or by its A-number.')
    @doc.argument('integers', 'The sequence of integers to lookup, separated by space only.')
    @doc.argument('a_number', 'The OEIS A-number to lookup.')
    @doc.invocation((), 'Get a sequence by searching for a random A-number (may not return results).')
    @doc.invocation(('integers',), 'Find a sequence matching these numbers.')
    @doc.invocation(('a_number',), 'Find the exact sequence with this A-number.')
    @doc.invocation(('integers', 'a_number'), False)
    @doc.example('1 1 2 3 5 8', 'Find the Fibonnacci numbers.')
    @doc.example('A018226', 'Find the magic numbers.')
    @doc.concurrent(1, BucketType.guild)
    @doc.cooldown(1, 10, BucketType.guild)
    async def oeis(self, ctx: Circumstances, integers: Greedy[int],
                   a_number: Optional[RegExp[Literal[r'A\d+'], Literal['A-number'], Literal['such as A0000045']]] = None):
        if integers:
            query = ' '.join([str(n) for n in integers])
        elif a_number:
            query = a_number[0]
        else:
            query = f'A{random.randrange(1, 1000000)}'
        try:
            sequence, num_results = await OEIS(ctx.session).get(query)
        except ValueError as e:
            reason = str(e)
            if not integers and not a_number:
                reason = f'{reason} (Searched for a random A-number {query})'
            return await ctx.reply(reason, delete_after=20)
        except aiohttp.ClientError:
            await ctx.reply('Network error while searching on OEIS')
            raise
        await ctx.reply_with_text_fallback(sequence.to_embed(), sequence.to_text())
        await ctx.send(f'({num_results - 1} more {pluralize(num_results - 1, "result")})')