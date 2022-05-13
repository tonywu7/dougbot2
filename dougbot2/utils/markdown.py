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
from math import floor
from textwrap import indent
from typing import Iterable, Literal
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from discord import Role
from discord.abc import GuildChannel, User
from discord.utils import escape_markdown
from django.utils.datastructures import MultiValueDict
from markdown import Markdown

RE_USER_MENTION = re.compile(r"<@(\d+)>")
RE_ROLE_MENTION = re.compile(r"<@&(\d+)>")
RE_CHANNEL_MENTION = re.compile(r"<#(\d+)>")

RE_CODE_START = re.compile(r"```(\w+)$")
RE_CODE_END = re.compile(r"^(.*?)```")

RE_URL = re.compile(r"https?://\S*(\.[^)\]<\s]+)+[^)\]<\s]*")

_TIMESTAMP_FORMATS = Literal[
    "yy/mm/dd",
    "hh:mm:ss",
    "hh:mm",
    "full",
    "long",
    "date",
    "relative",
]
TIMESTAMP_PROCESSOR: dict[_TIMESTAMP_FORMATS, str] = {
    "yy/mm/dd": "d",
    "hh:mm:ss": "T",
    "hh:mm": "t",
    "full": "F",
    "long": "f",
    "date": "D",
    "relative": "R",
}


def tag(obj) -> str:
    # TODO: remove
    if isinstance(obj, User):
        return f"<@{obj.id}>"
    if isinstance(obj, GuildChannel):
        return f"<#{obj.id}>"
    if isinstance(obj, Role):
        if obj.is_default():
            return "@everyone"
        return f"<@&{obj.id}>"
    return obj


def tag_literal(kind: str, val: int):
    """Format this integer as a Discord mention as if it is a Discord object."""
    return {
        "user": "<@%(val)s>",
        "member": "<@%(val)s>",
        "channel": "<#%(val)s>",
        "role": "<@&%(val)s>",
    }[kind] % {"val": val}


def em(s: str) -> str:
    """Format as italics."""
    return f"_{s}_"


def strong(s: str) -> str:
    """Format as bold."""
    return f"**{s}**"


def u(s: str) -> str:
    """Format as underline."""
    return f"__{s}__"


def code(s: str) -> str:
    """Format as monospace characters."""
    return f"`{s}`"


def pre(s: str, lang="") -> str:
    """Format as a code block, optionally with syntax highlighting."""
    return f"```{lang}\n{s}\n```"


def strike(s: str) -> str:
    """Format as a strikethrough."""
    return f"~~{s}~~"


def redact(s: str) -> str:
    """Format as redaction."""
    return f"||{s}||"


def blockquote(s: str) -> str:
    """Format as a blockquote.

    The > character is added at the beginnings
    of every new line.
    """
    return indent(s, "> ", predicate=lambda t: True)


def E(s: str) -> str:
    # TODO: use the emoji package
    """Format as a Discord emote by name."""
    return f":{s}:"


def a(text: str, href: str) -> str:
    """Format as a markdown hyperlink."""
    return f"[{text}]({href})"


def verbatim(text: str) -> str:
    """Escape all markdowns in the text and format it as a monospace string."""
    return code(escape_markdown(text))


def traffic_light(val: bool | None, strict=False):
    """Convert truthy values to the `green` emoji and falsy values to `red`.

    If `strict` is True, convert `None` to the `yellow` emoji.
    """
    if val:
        return "🟢"
    elif strict and val is None:
        return "🟡"
    else:
        return "⛔"


def pointer(d: Literal["N", "E", "S", "W"]) -> str:
    """Make an arrow pointing towards a direction."""
    return {
        "N": "↑",
        "E": "→",
        "S": "↓",
        "W": "←",
    }[d]


def _unmark_element(element, stream=None):
    # https://stackoverflow.com/a/54923798/10896407
    if stream is None:
        stream = StringIO()
    if element.text:
        stream.write(element.text)
    for sub in element:
        _unmark_element(sub, stream)
    if element.tail:
        stream.write(element.tail)
    return stream.getvalue()


def timestamp(
    t: datetime | float | int | str,
    f: Literal[
        "yy/mm/dd",
        "hh:mm:ss",
        "hh:mm",
        "full",
        "long",
        "date",
        "relative",
    ],
) -> str:
    """Create a Discord timestamp markdown from a timestamp.

    :param t: The timestamp
    :type t: Union[datetime, float, int, str]
    :param f: The displayed format
    :type f: Literal['yy/mm/dd', 'hh:mm:ss', 'hh:mm',
        'full', 'long', 'date', 'relative']
    """
    if isinstance(t, datetime):
        t = t.timestamp()
    if isinstance(t, str):
        t = float(t)
    # TODO: accept also directly specifying the format
    return f"<t:{floor(t):.0f}:{TIMESTAMP_PROCESSOR[f]}>"


Markdown.output_formats["plain"] = _unmark_element
_md = Markdown(output_format="plain")
_md.stripTopLevelTags = False


def untagged(text: str) -> str:
    """Remove all user/role/channel mentions and show their IDs instead."""
    text = RE_USER_MENTION.sub(r"user:\1", text)
    text = RE_ROLE_MENTION.sub(r"role:\1", text)
    text = RE_CHANNEL_MENTION.sub(r"channel:\1", text)
    return text


def unmarked(text: str) -> str:
    """Try to remove all markdowns from the string."""
    return _md.convert(text)


def unwrap_codeblock(text: str, lang: str = "") -> str:
    """Remove the opening and closing backticks from a code block.

    If `lang` is specified, assert that the code block is marked
    as this language too.
    """
    text = text.strip()
    sig = f"```{lang}"
    if not text.startswith(f"{sig}\n"):
        raise ValueError(f"Code block does not begin with {sig}")
    if not text.endswith("\n```"):
        raise ValueError("Code block does not end with ```")
    return text.removeprefix(f"{sig}\n").removesuffix("```")


def find_codeblock(text: str, langs: tuple[str, ...]) -> tuple[str, int]:
    """Find and return the first valid code blocks matching\
    this language from the text.

    :param text: The text to search
    :type text: str
    :param langs: Find only code blocks in these languages.
    :type langs: tuple[str, ...]
    :return: The code block with backticks stripped, and the position
    in the original string at which it ends.
    :rtype: tuple[str, int]
    """
    lines = iter(text.splitlines())
    passed = []
    block = []
    end = ""
    for line in lines:
        if not block:
            passed.append(line)
            matched = RE_CODE_START.search(line)
            if not matched:
                continue
            if matched.group(1) in langs:
                passed.append("")
                block.append(line)
            else:
                return "", 0
        else:
            matched = RE_CODE_END.search(line)
            if matched:
                block.append(matched.group(1))
                end = "```"
                break
            else:
                block.append(line)
    code = "\n".join(block[1:])
    length = len("\n".join(passed)) + len(code) + len(end)
    return code, length


def urlqueryset(u: str, **query) -> str:
    """Replace the query in this URL with these params."""
    url = urlsplit(u)
    par = MultiValueDict(parse_qs(url.query))
    par.update(query)
    q = urlencode(par)
    return urlunsplit((*url[:3], q, url[4]))


def sized(u: str, s: int) -> str:
    """Add a `size=` parameter to the URL.

    Used for Discord asset URLs.
    """
    return urlqueryset(u, size=s)


def rgba2int(r: int, g: int, b: int, a: int | None = None) -> int:
    """Convert an RGB(A) tuple to its integer representation (numeric value of the hex code)."""
    if a is None:
        return (r << 16) + (g << 8) + b
    else:
        return (r << 24) + (g << 16) + (b << 8) + a


def iter_urls(s: str) -> Iterable[str]:
    """Iterate over all URLs in text.

    A substring is consider a URL if Discord
    will display it as one.
    """
    for m in RE_URL.finditer(s):
        yield m.group(0)
