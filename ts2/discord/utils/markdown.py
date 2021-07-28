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

import re
from datetime import datetime
from io import StringIO
from textwrap import indent
from typing import Literal

from discord import Role
from discord.abc import GuildChannel, User
from discord.utils import escape_markdown
from markdown import Markdown

RE_USER_MENTION = re.compile(r'<@(\d+)>')
RE_ROLE_MENTION = re.compile(r'<@&(\d+)>')
RE_CHANNEL_MENTION = re.compile(r'<#(\d+)>')

ARROWS_E = {
    'white': '<:mta_arrowE:856190628857249792>',
    'red': '<:mta_arrowE_red:856460793330794536>',
}
ARROWS_W = {
    'white': '<:mta_arrowW:856190628399153164>',
    'red': '<:mta_arrowW_red:856460793323323392>',
}
ARROWS_N = {
    'white': '<:mta_arrowN:856190628831952906>',
}
ARROWS_S = {
    'white': '<:mta_arrowS:856190628823826432>',
}


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


def a(text: str, href: str) -> str:
    return f'[{text}]({href})'


def verbatim(text: str) -> str:
    return code(escape_markdown(text))


def traffic_light(val: bool | None, strict=False):
    if val:
        return '🟢'
    elif strict and val is None:
        return '🟡'
    else:
        return '⛔'


def arrow(d: Literal['N', 'E', 'S', 'W']) -> str:
    return {
        'N': ARROWS_N['white'],
        'E': ARROWS_E['white'],
        'S': ARROWS_S['white'],
        'W': ARROWS_W['white'],
    }[d]


def mta_arrow_bracket(s: str, color='white') -> str:
    return f'{ARROWS_E[color]} {s} {ARROWS_W[color]}'


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


_TIMESTAMP_FORMATS = Literal[
    'yy/mm/dd', 'hh:mm:ss', 'hh:mm',
    'full', 'long', 'date', 'relative',
]
TIMESTAMP_PROCESSOR: dict[_TIMESTAMP_FORMATS, str] = {
    'yy/mm/dd': 'd',
    'hh:mm:ss': 'T',
    'hh:mm': 't',
    'full': 'F',
    'long': 'f',
    'date': 'D',
    'relative': 'R',
}


def timestamp(t: datetime | float | int, f: _TIMESTAMP_FORMATS) -> str:
    if isinstance(t, datetime):
        t = t.timestamp()
    return f'<t:{t:.0f}:{TIMESTAMP_PROCESSOR[f]}>'


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
