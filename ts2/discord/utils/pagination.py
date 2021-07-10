# pagination.py
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

import asyncio
import enum
import logging
import re
import time
from collections.abc import Callable, Iterable, Iterator, Sequence, Sized
from textwrap import shorten
from typing import Generic, TypeVar, Union

from discord import (Client, Embed, Emoji, Message, PartialEmoji,
                     RawReactionActionEvent)
from more_itertools import split_before

from . import events
from .duckcord.embeds import Embed2
from .markdown import strong, u

RE_BLOCKQUOTE = re.compile(r'^> ')
RE_PRE_BORDER = re.compile(r'^```.*$')

S = TypeVar('S', bound=Sized)

PageContent = tuple[Union[str, None], Union[Embed2, None]]
PageProvider = Callable[[PartialEmoji], PageContent]


class ParagraphStream:

    class BLOCK(enum.Enum):
        PRESERVE = 0
        INLINE = 2

    def __init__(self, separator: str = ' ', pre: BLOCK = BLOCK.PRESERVE, blockquote: BLOCK = BLOCK.PRESERVE):
        self.lines: list[str] = []
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


def trunc_for_field(text: str) -> str:
    return shorten(text, width=960, placeholder='... (truncated)')


def page_plaintext(sections: tuple[str, str], title=None, description=None, footer=None, divider='') -> str:
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


def page_embed(sections: tuple[str, str], title=Embed.Empty, description=Embed.Empty, footer=Embed.Empty) -> Embed:
    embed = Embed(title=title, description=description)
    for title, body in sections:
        embed.add_field(name=title, value=body, inline=False)
    if footer:
        embed.set_footer(text=footer)
    return embed


def page_embed2(sections: tuple[str, str], title=Embed.Empty, description=Embed.Empty, footer=Embed.Empty) -> Embed2:
    embed = Embed2(title=title, description=description).set_footer(text=footer)
    for title, body in sections:
        embed = embed.add_field(name=title, value=body, inline=False)
    return embed


def limit_results(results: list[str], limit: int) -> list[str]:
    if len(results) <= limit:
        return results
    return results[:limit] + [f'({len(results) - limit} more)']


def chapterize_items(items: Iterable[Generic[S]], break_at: int) -> Iterable[list[S]]:
    current_len = 0

    def splitter(item: S):
        nonlocal current_len
        size = len(item)
        if current_len + size > break_at:
            current_len = 0
            return True
        current_len += size
        return False

    return split_before(items, splitter)


def format_page_number(idx: int, total: int, sep: str = '/'):
    if idx < 0:
        idx = total + idx
    if idx < 0 or idx >= total:
        raise ValueError
    return f'{idx + 1}{sep}{total}'


class Paginator:
    def __init__(
        self, client: Client, message: Message, ttl: float, *,
        users: Iterable[int], emotes: list[Emoji | PartialEmoji | str],
        provider: PageProvider,
    ) -> None:
        self.log = logging.getLogger('discord.paginator')

        self.client = client
        self.message = message
        self.provider = provider

        self.ttl = ttl
        self.end: float

        self.emotes: dict[int | str, str | Emoji | PartialEmoji] = {}
        for e in emotes:
            if isinstance(e, str):
                self.emotes[e] = e
            elif isinstance(e, (Emoji, PartialEmoji)):
                self.emotes[e.id] = e

        tests = (
            events.emote_no_bots,
            events.emote_added,
            events.emote_matches(*self.emotes.keys()),
            events.reaction_from(*users),
            events.reaction_on(message.id),
        )

        def check(evt: RawReactionActionEvent, tests=tests) -> bool:
            return all(t(evt) for t in tests)

        self.check = check

    async def init(self):
        for emote in self.emotes:
            await self.message.add_reaction(emote)

    async def cleanup(self):
        try:
            for emote in self.emotes:
                await self.message.clear_reaction(emote)
        except Exception:
            pass

    async def run(self):
        self.end = time.perf_counter() + self.ttl

        try:
            await self.init()
        except Exception as e:
            self.log.debug(
                f'{type(e).__name__} while starting paginator: {e}\n'
                f'Message: {self.message.id}',
            )
            return

        while True:
            ts = time.perf_counter()
            if ts > self.end:
                break
            timeout = self.end - ts
            try:
                evt = await self.client.wait_for(
                    'raw_reaction_add',
                    check=self.check, timeout=timeout,
                )
            except asyncio.TimeoutError:
                continue

            evt: RawReactionActionEvent
            await self.message.remove_reaction(evt.emoji, evt.member)

            text, embed = self.provider(evt.emoji)
            if not text and not embed:
                continue
            await self.message.edit(content=text, embed=embed)

        await self.cleanup()


class NullPaginator(Paginator):
    def __init__(self) -> None:
        pass

    async def run(self):
        return


class Pagination:
    def __init__(self, content: Sequence[PageContent]) -> None:
        self.content = content
        self.actions = {
            '⏮': lambda idx: 0,
            '⏪': lambda idx: idx - 1,
            '⏩': lambda idx: idx + 1,
            '⏭': lambda idx: len(content) - 1,
        }

    def __getitem__(self, k: int) -> PageContent:
        text, embed = self.content[k]
        return (self.text_transform(k, text),
                self.embed_transform(k, embed))

    def index_setter(self) -> PageProvider:
        index = 0

        def provider(emote: PartialEmoji) -> PageContent:
            nonlocal index
            idx: int = self.actions[emote.name](index)
            if idx < 0 or idx >= len(self.content) or idx == index:
                return None, None
            index = idx
            return self[idx]

        return provider

    def __call__(self, client: Client, message: Message, ttl: int, *users: int) -> Paginator:
        if len(self.content) > 1:
            return Paginator(client, message, ttl, users=users,
                             provider=self.index_setter(), emotes=self.actions.keys())
        return NullPaginator()

    def text_transform(self, idx: int, body: str) -> str:
        return body

    def embed_transform(self, idx: int, embed: Embed2) -> Embed2:
        return embed


class TextPagination(Pagination):
    def __init__(self, texts: Sequence[str], title: str) -> None:
        super().__init__([(s, None) for s in texts])
        self.title = title

    def text_transform(self, idx: int, body: str) -> str:
        if not body:
            return
        return f'{strong(self.title)} ({format_page_number(idx, len(self.content))})\n\n{body}'


class EmbedPagination(Pagination):
    def __init__(self, embeds: Sequence[Embed2], title: str, set_timestamp: bool = True) -> None:
        super().__init__([(None, e) for e in embeds])
        self.title = title
        self.timestamp = set_timestamp

    def embed_transform(self, idx: int, embed: Embed2) -> Embed2:
        if not embed:
            return
        embed = embed.set_title(f'{self.title} ({format_page_number(idx, len(self.content))})')
        if self.timestamp:
            embed = embed.set_timestamp()
        return embed
