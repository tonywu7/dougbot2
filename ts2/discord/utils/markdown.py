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

import random
import re
from collections import deque
from datetime import datetime
from io import StringIO
from math import floor
from statistics import mean
from textwrap import indent
from typing import Literal
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from discord import Role
from discord.abc import GuildChannel, User
from discord.utils import escape_markdown
from django.utils.datastructures import MultiValueDict
from markdown import Markdown

RE_USER_MENTION = re.compile(r'<@(\d+)>')
RE_ROLE_MENTION = re.compile(r'<@&(\d+)>')
RE_CHANNEL_MENTION = re.compile(r'<#(\d+)>')

RE_CODE_START = re.compile(r'```(\w+)$')
RE_CODE_END = re.compile(r'^(.*?)```')

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
        'N': '↑',
        'E': '→',
        'S': '↓',
        'W': '←',
    }[d]


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


def timestamp(t: datetime | float | int, f: Literal[
    'yy/mm/dd', 'hh:mm:ss', 'hh:mm',
    'full', 'long', 'date', 'relative',
]) -> str:
    if isinstance(t, datetime):
        t = t.timestamp()
    return f'<t:{floor(t):.0f}:{TIMESTAMP_PROCESSOR[f]}>'


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


def unwrap_codeblock(text: str, lang: str) -> str:
    text = text.strip()
    sig = f'```{lang}'
    if not text.startswith(f'{sig}\n'):
        raise ValueError(f'Code block does not begin with {sig}')
    if not text.endswith('\n```'):
        raise ValueError('Code block does not end with ```')
    return text.removeprefix(f'{sig}\n').removesuffix('```')


def find_codeblock(text: str, langs: tuple[str, ...]) -> tuple[str, int]:
    lines = iter(text.splitlines())
    passed = []
    block = []
    end = ''
    for line in lines:
        if not block:
            passed.append(line)
            matched = RE_CODE_START.search(line)
            if not matched:
                continue
            if matched.group(1) in langs:
                passed.append('')
                block.append(line)
            else:
                return '', 0
        else:
            matched = RE_CODE_END.search(line)
            if matched:
                block.append(matched.group(1))
                end = '```'
                break
            else:
                block.append(line)
    code = '\n'.join(block[1:])
    length = len('\n'.join(passed)) + len(code) + len(end)
    return code, length


def urlqueryset(u: str, **query) -> str:
    url = urlsplit(u)
    par = MultiValueDict(parse_qs(url.query))
    par.update(query)
    q = urlencode(par)
    return urlunsplit((*url[:3], q, url[4]))


def sized(u: str, s: int) -> str:
    return urlqueryset(u, size=s)


def spongebob(
    s: str, ratio: float = .5,
    *, lookback: int = 2,
    bias: float = .75,
) -> tuple[str, bool]:
    history: deque[bool] = deque(maxlen=lookback)
    buffer = []
    has_alpha = False
    complement = 1 - bias
    for char in s:
        if not char.isalpha():
            buffer.append(char)
            continue
        has_alpha = True
        change = random.random()
        if history:
            if mean(history) < .5:
                change = change * bias + complement
            else:
                change = change * bias
        if change < ratio:
            buffer.append(char.lower())
            history.append(False)
        else:
            buffer.append(char.upper())
            history.append(True)
    res = ''.join(buffer)
    return res, has_alpha


def rgba2int(r: int, g: int, b: int, a: int | None = None) -> int:
    if a is None:
        return (r << 16) + (g << 8) + b
    else:
        return (r << 24) + (g << 16) + (b << 8) + a
