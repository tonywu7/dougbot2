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

import enum
import re
from collections.abc import Callable, Iterable, Iterator, Sequence, Sized
from typing import Generic, Literal, TypeVar, Union

import attr
from discord import (Client, Embed, Member, Message, PartialEmoji,
                     RawReactionActionEvent)
from discord.ext.commands import Context
from more_itertools import peekable, split_before

from .duckcord.embeds import Embed2, EmbedField
from .events import EmoteResponder
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


def trunc_for_field(text: str, size=960, placeholder=' ... (truncated)') -> str:
    actual_size = size - len(placeholder)
    if len(text) >= actual_size:
        return f'{text[:actual_size]}{placeholder}'
    return text


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


def chapterize_fields(
    fields: Iterable[EmbedField],
    pagesize: int = 720,
    linebreak: set[Literal[
        'exact',
        'whitespace',
        'newline',
    ]] = frozenset({'whitespace'}),
) -> Iterator[list[EmbedField]]:
    if sum(len(f) for f in fields) < pagesize:
        yield [*fields]
        return
    page: list[EmbedField] = []
    fields = peekable(fields)
    while fields:
        size = sum(len(f) for f in page)
        next_field = fields.peek()
        next_len = len(next_field)
        if size and size + next_len > pagesize:
            yield page
            page = [next(fields)]
        elif next_len > pagesize:
            head, *tails = [*chapterize(
                next_field.value, pagesize,
                linebreak=linebreak, leeway=pagesize,
                maxsplit=1, closing='', opening='',
            )]
            next(fields)
            page.append(attr.evolve(next_field, value=head))
            fields.prepend(*[attr.evolve(next_field, value=v) for v in tails])
        else:
            page.append(next(fields))
    if page:
        yield page


def chapterize(
    text: str, length: int = 1920, leeway=32,
    closing=' ... ', opening='(continued) ',
    linebreak: Literal[
        'exact',
        'whitespace',
        'newline',
    ] = 'whitespace',
    maxsplit: int = float('inf'),
) -> Iterator[str]:
    if len(text) < length:
        yield text
        return
    split = 0
    while True:
        cutoff = text[length:length + 1]
        if not cutoff:
            yield text
            return
        if linebreak == 'exact':
            yield text[0:length] + closing
            text = opening + text[length + 1:]
            continue
        if linebreak == 'newline':
            def check(s: str):
                return s == '\n'
        elif linebreak == 'whitespace':
            check = str.isspace
        for i in range(length - 1, length - leeway - 1, -1):
            if check(text[i:i + 1]):
                break
        else:
            before = text[0:length - leeway] + closing
            if before:
                yield before
            text = opening + text[length - leeway:]
            split += 1
            if split > maxsplit:
                yield text
                return
            continue
        before = yield text[0:i] + closing
        if before:
            yield before
        text = opening + text[i + 1:]
        if split > maxsplit:
            yield text
            return


def format_page_number(idx: int, total: int, sep: str = '/'):
    if idx < 0:
        idx = total + idx
    if idx < 0 or idx >= total:
        raise ValueError
    return f'{idx + 1}{sep}{total}'


class Paginator(EmoteResponder):
    def __init__(self, provider: PageProvider, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.provider = provider

    async def handle(self, event: RawReactionActionEvent) -> bool:
        text, embed = self.provider(event.emoji)
        if not text and not embed:
            return
        await self.message.edit(content=text, embed=embed)


class NullPaginator(Paginator):
    def __init__(self) -> None:
        pass

    async def run(self):
        return

    async def on_start(self):
        return

    async def on_finish(self):
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

    def get_text(self, k: int) -> str:
        return self.text_transform(k, self.content[k][0])

    def get_embed(self, k: int) -> str:
        return self.embed_transform(k, self.content[k][1])

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

    async def reply(self, ctx: Context, ttl: int) -> tuple[Message, Paginator]:
        text, embed = self[0]
        msg = await ctx.reply(content=text, embed=embed)
        return msg, self(ctx.bot, msg, ttl, ctx.author)

    def __call__(self, client: Client, message: Message, ttl: int, *users: Union[int, Member]) -> Paginator:
        if len(self.content) > 1:
            return Paginator(self.index_setter(), client=client, message=message,
                             ttl=ttl, users=users, emotes=self.actions.keys())
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
