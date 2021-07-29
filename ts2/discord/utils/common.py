from typing import Union

from discord import DMChannel, Message, TextChannel
from discord.ext.commands import Context

from .async_ import (async_first, async_get, async_list,  # noqa: F401
                     async_save)
from .duckcord.color import Color2  # noqa: F401
from .duckcord.embeds import Embed2  # noqa: F401
from .duckcord.permissions import PermissionOverride  # noqa: F401
from .duckcord.permissions import Permissions2  # noqa: F401
from .events import (DeleteResponder, EmoteResponder, Responder,  # noqa: F401
                     emote_added, emote_matches, emote_no_bots, event_filter,
                     run_responders, start_responders)
from .markdown import (E, a, arrow, blockquote, code, em, pre,  # noqa: F401
                       redact, strike, strong, tag, tag_literal, timestamp,
                       traffic_light, u, unmarked, untagged, verbatim)
from .pagination import (EmbedPagination, ParagraphStream,  # noqa: F401
                         TextPagination, chapterize_items, limit_results,
                         page_embed2, page_plaintext, trunc_for_field)


def is_direct_message(ctx: Union[Message, Context, TextChannel]):
    return isinstance(ctx, DMChannel) or isinstance(ctx.channel, DMChannel)
