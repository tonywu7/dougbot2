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
from typing import Generic, Optional, TypeVar, Union

import attr
from discord import (Client, Member, Message, PartialEmoji,
                     RawReactionActionEvent)
from discord.ext.commands import Context
from duckcord.embeds import Embed2, EmbedField
from more_itertools import peekable, split_before

from .events import EmoteResponder
from .markdown import strong

RE_BLOCKQUOTE = re.compile(r'^> ')
RE_PRE_BORDER = re.compile(r'^```.*$')

S = TypeVar('S', bound=Sized)

PageContent = tuple[Union[str, None], Union[Embed2, None]]
PageProvider = Callable[[PartialEmoji], PageContent]


class ParagraphStream:
    """Continuous iterator over multiple strings."""

    class BLOCK(enum.Enum):
        PRESERVE = 0
        INLINE = 2

    def __init__(self, separator: str = ' ', pre: BLOCK = BLOCK.PRESERVE, blockquote: BLOCK = BLOCK.PRESERVE):
        self.lines: list[str] = []
        self.sep = separator
        self.pre = pre
        self.blockquote = blockquote

    def append(self, text: str):
        """Add text to the end of string."""
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
    """Limit the length of a string if it exceeds a size limit."""
    actual_size = size - len(placeholder)
    if len(text) >= actual_size:
        return f'{text[:actual_size]}{placeholder}'
    return text


def chapterize_items(items: Iterable[Generic[S]], break_at: int) -> Iterable[list[S]]:
    """Break a sequence of items with sizes into groups,\
    breaking whenever the size of the group reaches a threshold."""
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


def chapterize_fields(fields: Iterable[EmbedField], pagesize: int = 720,
                      linebreak=lambda c: c == '\n') -> Iterator[list[EmbedField]]:
    """Rearrange a list of embed fields and breaking fields longer than a certain size into\
    separate fields sharing the same name."""
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
            page = []
        if next_len > pagesize:
            head, *tails = [*chapterize(next_field.value, pagesize,
                                        pred=linebreak, maxsplit=1)]
            next(fields)
            page.append(attr.evolve(next_field, value=head))
            fields.prepend(*[attr.evolve(next_field, value=v) for v in tails])
        else:
            page.append(next(fields))
    if page:
        yield page


# From ddarknut. Blessed.
def chapterize(text: str, maxlen: int, pred: Callable[[str], bool] = str.isspace,
               *, hyphen='-', maxsplit=float('inf')) -> Iterable[str]:
    """Break long text into smaller parts of roughly the same size while\
    avoiding breaking inside words/lines."""

    if len(hyphen) > maxlen:
        raise ValueError('Hyphenation cannot be longer than length limit.')
    if not text or maxsplit < 1:
        yield text
        return

    end = sep = begin = 0
    splits = 0
    while begin < len(text):
        if end >= len(text) or splits >= maxsplit:
            yield text[begin:]
            return
        if pred(text[end]):
            sep = end
        end += 1
        if end > begin + maxlen:
            if sep > begin:
                end = sep
                yield text[begin:end]
            else:
                end -= len(hyphen) + 1
                yield text[begin:end] + hyphen
            begin = end
            splits += 1


def format_page_number(idx: int, total: int, sep: str = '/'):
    """Indicate an item's position, such as `1/6` for the first item\
    in a total of six items."""
    if idx < 0:
        idx = total + idx
    if idx < 0 or idx >= total:
        raise ValueError
    return f'{idx + 1}{sep}{total}'


class Paginator(EmoteResponder):
    """An EmoteResponder that edits message contents on reactions.

    Initialized by the Pagination class.
    """

    def __init__(self, provider: PageProvider, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.provider = provider

    async def handle(self, event: RawReactionActionEvent) -> bool:
        """Change message content on reactions."""
        text, embed = self.provider(event.emoji)
        if not text and not embed:
            return
        await self.message.edit(content=text, embed=embed)


class NullPaginator(Paginator):
    """A paginator that does nothing.

    Used when there is only one page (and thus reactions are not needed).
    """

    def __init__(self) -> None:
        pass

    async def run(self):
        return

    async def on_start(self):
        return

    async def on_finish(self):
        return


class Pagination:
    """Create a paginator from multiple "pages" of text/embeds.

    Pagination objects are callable and returns a Paginator when called.
    Thus Pagination objects are reusable, while Paginators are not.
    """

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
        """Get the text at page `k` (zero-indexed), applying text transforms."""
        return self.text_transform(k, self.content[k][0])

    def get_embed(self, k: int) -> Embed2:
        """Get the embed at page `k` (zero-indexed), applying text transforms."""
        return self.embed_transform(k, self.content[k][1])

    def index_setter(self) -> PageProvider:
        """Return a callable that returns the corresponding page when called with an emote."""
        index = 0

        def provider(emote: PartialEmoji) -> PageContent:
            nonlocal index
            idx: int = self.actions[emote.name](index)
            if idx < 0 or idx >= len(self.content) or idx == index:
                return None, None
            index = idx
            return self[idx]

        return provider

    def __call__(self, client: Client, message: Message, ttl: int, *users: Union[int, Member]) -> Paginator:
        """Make a Paginator from this Pagination to be used in message replies."""
        if len(self.content) > 1:
            return Paginator(self.index_setter(), client=client, message=message,
                             ttl=ttl, users=users, emotes=self.actions.keys())
        return NullPaginator()

    def text_transform(self, idx: int, body: str) -> str:
        """Modify the text page before returning it.

        Subclasses can override this method for custom behaviors, such
        as adding page numbers.
        """
        return body

    def embed_transform(self, idx: int, embed: Embed2) -> Embed2:
        """Modify the embed page before returning it.

        Subclasses can override this method for custom behaviors, such
        as adding page numbers.
        """
        return embed


class TextPagination(Pagination):
    """A Pagination that provides only text content."""

    def __init__(self, texts: Sequence[str], title: str) -> None:
        super().__init__([(s, None) for s in texts])
        self.title = title

    def text_transform(self, idx: int, body: str) -> str:
        """Add a title and a page number to each page."""
        if not body:
            return
        return f'{strong(self.title)} ({format_page_number(idx, len(self.content))})\n\n{body}'


class EmbedPagination(Pagination):
    """A Pagination that provides only embed content."""

    def __init__(self, embeds: Sequence[Embed2], title: Optional[str], set_timestamp: bool = True) -> None:
        super().__init__([(None, e) for e in embeds])
        self.title = title
        self.timestamp = set_timestamp

    def embed_transform(self, idx: int, embed: Embed2) -> Embed2:
        """Set the page number in the title and optionally the timestamp."""
        if not embed:
            return
        if self.title:
            embed = embed.set_title(f'{self.title} ({format_page_number(idx, len(self.content))})')
        if self.timestamp:
            embed = embed.set_timestamp()
        return embed

    def to_dict(self):
        """Convert the first page to a dict.

        This allows the Pagination object to be passed where `discord.abc.Messageable`
        expects an `Embed` object.
        """
        return self.get_embed(0).to_dict()

    def with_context(self, ctx: Context, ttl=600):
        """Create a Paginator object attached to this Context."""
        def from_message(m: Message):
            return self(ctx.bot, m, ttl, ctx.author)
        return from_message
