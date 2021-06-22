# markdown.py
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

import enum
import re
from io import StringIO
from textwrap import indent, shorten
from typing import Iterator, List, Tuple

from discord import Embed, Role
from discord.abc import GuildChannel, User
from discord.ext.commands import Context
from discord.ext.commands.view import StringView
from markdown import Markdown

RE_USER_MENTION = re.compile(r'<@(\d+)>')
RE_ROLE_MENTION = re.compile(r'<@&(\d+)>')
RE_CHANNEL_MENTION = re.compile(r'<#(\d+)>')
RE_BLOCKQUOTE = re.compile(r'^> ')
RE_PRE_BORDER = re.compile(r'^```.*$')

ARROWS_E = {
    'white': '<:mta_arrowE:856190628857249792>',
    'red': '<:mta_arrowE_red:856460793330794536>',
}
ARROWS_W = {
    'white': '<:mta_arrowW:856190628399153164>',
    'red': '<:mta_arrowW_red:856460793323323392>',
}


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


def tag_literal(kind: str, val: int):
    return {
        'user': '<@%(val)d>',
        'member': '<@%(val)d>',
        'channel': '<#%(val)d>',
        'role': '<@&%(val)d>',
    }[kind] % {'val': val}


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


def a(href: str, text: str) -> str:
    return f'[{text}]({href})'


def traffic_light(val: bool | None, strict=False):
    if val:
        return '🟢'
    elif strict and val is None:
        return '🟡'
    else:
        return '⛔'


def mta_arrow_bracket(s: str, color='white') -> str:
    return f'{ARROWS_E[color]} {s} {ARROWS_W[color]}'


def indicate_eol(s: StringView, color='white') -> str:
    return f'{s.buffer[:s.index + 1]} {ARROWS_W[color]}'


def indicate_extra_text(s: StringView, color='white') -> str:
    return f'{s.buffer[:s.index]} {ARROWS_E[color]} {s.buffer[s.index:]} {ARROWS_W[color]}'


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


class ParagraphStream:

    class BLOCK(enum.Enum):
        PRESERVE = 0
        INLINE = 2

    def __init__(self, separator: str = ' ', pre: BLOCK = BLOCK.PRESERVE, blockquote: BLOCK = BLOCK.PRESERVE):
        self.lines: List[str] = []
        self.sep = separator
        self.pre = pre
        self.blockquote = blockquote

    def append(self, text: str):
        self.lines.extend(filter(None, text.split('\n')))

    def __len__(self) -> int:
        return sum(len(s) for s in self.lines)

    def __iter__(self) -> Iterator[str]:
        buffer = []
        line_iter = iter(self.lines)

        if self.blockquote is self.BLOCK.PRESERVE:
            def blockquote(line: str):
                nonlocal buffer
                if buffer:
                    yield self.sep.join(buffer)
                    buffer = []
                yield line
        else:
            def blockquote(line: str):
                buffer.append(RE_BLOCKQUOTE.sub('', line))
                return []

        if self.pre is self.BLOCK.PRESERVE:
            def pre(line: str):
                nonlocal buffer
                if buffer:
                    yield self.sep.join(buffer)
                    buffer = []
                yield line
                for line in line_iter:
                    yield line
                    if RE_PRE_BORDER.match(line):
                        return
        else:
            def pre(line: str):
                return []

        while True:
            try:
                line = next(line_iter)
            except StopIteration:
                break

            if RE_BLOCKQUOTE.match(line):
                yield from blockquote(line)
            elif RE_PRE_BORDER.match(line):
                yield from pre(line)
            else:
                buffer.append(line)

        if buffer:
            yield self.sep.join(buffer)


def chapterize(text: str, length: int = 1920, leeway=16,
               closing=' ... ', opening='(continued) ') -> Iterator[str]:
    if len(text) < length:
        yield text
        return
    while True:
        cutoff = text[length:length + 1]
        if not cutoff:
            yield text
            return
        for i in range(length - 1, length - leeway - 1, -1):
            if text[i:i + 1].isspace():
                break
        else:
            yield text[0:length - leeway] + '-' + closing
            text = opening + text[length - leeway:]
            continue
        yield text[0:i] + closing
        text = opening + text[i + 1:]


Markdown.output_formats['plain'] = unmark_element
_md = Markdown(output_format='plain')
_md.stripTopLevelTags = False


def untagged(text: str) -> str:
    text = RE_USER_MENTION.sub(r'user:\1', text)
    text = RE_ROLE_MENTION.sub(r'role:\1', text)
    text = RE_CHANNEL_MENTION.sub(r'channel:\1', text)
    return text


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


def limit_results(results: List[str], limit: int) -> List[str]:
    if len(results) <= limit:
        return results
    return results[:limit] + [f'({len(results) - limit} more)']
