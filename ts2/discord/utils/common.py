from collections.abc import MutableMapping
from datetime import timezone
from typing import Optional, TypeVar, Union

from discord import DMChannel, Message, TextChannel
from discord.ext.commands import Context

from .async_ import (async_first, async_get, async_list,  # noqa: F401
                     async_save)
from .datetime import utcnow  # noqa: F401
from .duckcord.color import Color2  # noqa: F401
from .duckcord.embeds import Embed2, EmbedField  # noqa: F401
from .duckcord.permissions import PermissionOverride  # noqa: F401
from .duckcord.permissions import Permissions2, get_total_perms  # noqa: F401
from .events import (DeleteResponder, EmoteResponder, Responder,  # noqa: F401
                     emote_added, emote_matches, emote_no_bots, event_filter,
                     run_responders, start_responders)
from .markdown import (E, a, arrow, blockquote, code, em, pre,  # noqa: F401
                       redact, sized, strike, strong, tag, tag_literal,
                       timestamp, traffic_light, u, unmarked, untagged,
                       unwrap_codeblock, urlqueryset, verbatim)
from .pagination import (EmbedPagination, ParagraphStream,  # noqa: F401
                         TextPagination, chapterize, chapterize_fields,
                         chapterize_items, limit_results, page_embed2,
                         page_plaintext, trunc_for_field)
from .response import ResponseInit  # noqa: F401

JS_BIGINT = 2 ** 53
_KT = TypeVar('_KT')
_VT = TypeVar('_VT')


def is_direct_message(ctx: Union[Message, Context, TextChannel]):
    return isinstance(ctx, DMChannel) or isinstance(ctx.channel, DMChannel)


def serialize_message(message: Message):
    author = message.author
    return {
        'id': message.id,
        'created_at': message.created_at.replace(tzinfo=timezone.utc).isoformat(),
        'author': {
            'id': author.id,
            'name': str(author),
            'display_name': author.display_name,
            'avatar_url': str(author.avatar_url),
        },
        'content': message.content,
        'embeds': [e.to_dict() for e in message.embeds],
        'files': [f.url for f in message.attachments],
    }


class BigIntDict(MutableMapping[_KT, _VT]):
    def __init__(self, mapping: Optional[MutableMapping[_KT, _VT]]) -> None:
        if mapping:
            self._map = {self._convert(k): v for k, v in mapping.items()}
        else:
            self._map = {}

    def _convert(self, k: Union[str, int]):
        if isinstance(k, int):
            return k
        try:
            num_k = int(k)
        except ValueError:
            return k
        if num_k < JS_BIGINT:
            return k
        return num_k

    def __getitem__(self, k):
        return self._map[self._convert(k)]

    def __setitem__(self, k, v):
        self._map[self._convert(k)] = v

    def __delitem__(self, k):
        del self._map[self._convert(k)]

    def __iter__(self):
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._map)
