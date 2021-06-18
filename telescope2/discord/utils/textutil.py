# textutil.py
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

from io import StringIO
from textwrap import indent, shorten
from typing import Tuple

from discord import Embed, Role
from discord.abc import GuildChannel, User
from discord.ext.commands import Context
from markdown import Markdown


def trimmed_msg(ctx: Context) -> str:
    return ctx.message.content[len(ctx.prefix) + len(ctx.command.name) + 1:]


def tag(obj) -> str:
    if isinstance(obj, User):
        return f'<@{obj.id}>'
    if isinstance(obj, GuildChannel):
        return f'<#{obj.id}>'
    if isinstance(obj, Role):
        if obj.is_default():
            return '@everyone'
        return f'<@&{obj.id}>'
    return obj


def em(s: str) -> str:
    return f'_{s}_'


def strong(s: str) -> str:
    return f'**{s}**'


def u(s: str) -> str:
    return f'__{s}__'


def code(s: str) -> str:
    return f'`{s}`'


def pre(s: str, lang='') -> str:
    return f'```{lang}\n{s}\n```'


def strike(s: str) -> str:
    return f'~~{s}~~'


def redact(s: str) -> str:
    return f'||{s}||'


def blockquote(s: str) -> str:
    return indent(s, '> ', predicate=lambda t: True)


def E(s: str) -> str:
    return f':{s}:'


def traffic_light(val: bool | None, strict=False):
    if val:
        return '🟢'
    elif strict and val is None:
        return '🟡'
    else:
        return '⛔'


def unmark_element(element, stream=None):
    # https://stackoverflow.com/a/54923798/10896407
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


Markdown.output_formats['plain'] = unmark_element
_md = Markdown(output_format='plain')
_md.stripTopLevelTags = False


def unmarked(text: str) -> str:
    return _md.convert(text)


def trunc_for_field(text: str) -> str:
    return shorten(text, width=960, placeholder='... (truncated)')


def page_plaintext(sections: Tuple[str, str], title=None, description=None, footer=None, divider='') -> str:
    lines = []
    if title:
        lines.append(u(strong(title)))
        if divider is not None:
            lines.append(divider)
    if description:
        lines.append(description)
        if divider is not None:
            lines.append(divider)
    for title, body in sections:
        lines.append(strong(title))
        lines.append(body)
        if divider is not None:
            lines.append(divider)
    if footer:
        lines.append(footer)
    return '\n'.join(lines)


def page_embed(sections: Tuple[str, str], title=Embed.Empty, description=Embed.Empty, footer=Embed.Empty) -> Embed:
    embed = Embed(title=title, description=description)
    for title, body in sections:
        embed.add_field(name=title, value=body, inline=False)
    if footer:
        embed.set_footer(text=footer)
    return embed
