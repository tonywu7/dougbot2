# command.py
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

from functools import cache

from discord.ext.commands import command
from duckcord.color import Color2
from duckcord.embeds import Embed2, EmbedField

from ...context import Circumstances
from ...exts import autodoc
from ...exts.autodoc import Environment
from ...utils.checks import can_embed
from ...utils.dm import accepts_dms
from ...utils.pagination import (EmbedPagination, chapterize_fields,
                                 chapterize_items)


@cache
def get_help_toc(env: Environment, maxlen: int = 500) -> EmbedPagination:
    manual = env.manual
    fields = [EmbedField(**f) for f in manual.export['fields']]
    chapters = chapterize_items(fields, maxlen)
    embeds = [Embed2(fields=chapter, color=Color2.blue()) for chapter in chapters]
    embeds = [e.set_footer(text=('Use "help [command]" here to see'
                                 ' how to use a command'))
              for e in embeds]
    return EmbedPagination(embeds, 'Help', True)


@cache
def get_cmd_help(env: Environment, query: str, maxlen: int = 500) -> EmbedPagination:
    manual = env.manual
    doc = manual.lookup(query)
    sections = [EmbedField(f['name'], f['value'], False) for f
                in doc.export['fields'] if f['value']]
    chapters = chapterize_fields(sections, maxlen)
    embeds = [Embed2(fields=chapter) for chapter in chapters]
    title = f'Help: {doc.call_sign}'
    embeds = [e.set_description(doc.description) for e in embeds]
    return EmbedPagination(embeds, title, False)


@command('help')
@accepts_dms
@autodoc.description('Get help about commands.')
@autodoc.argument('query', 'A command name, such as "echo" or "prefix set".')
@autodoc.invocation((), 'See all commands.')
@autodoc.invocation(('query',), 'See help for a command.')
@can_embed
async def help_command(ctx: Circumstances, query: str = ''):
    if not query:
        pagination = get_help_toc()
    else:
        pagination = get_cmd_help(query)
    res = (ctx.response(ctx, embed=pagination)
           .responder(pagination.with_context(ctx)))
    if not query:
        res = res.dm().success()
    await res.run()
