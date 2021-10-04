# common.py
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

from duckcord.color import Color2  # noqa: F401
from duckcord.embeds import Embed2, EmbedField  # noqa: F401
from duckcord.permissions import PermissionOverride  # noqa: F401
from duckcord.permissions import Permissions2, get_total_perms  # noqa: F401

from .async_ import (async_first, async_get, async_list,  # noqa: F401
                     async_save)
from .checks import (can_embed, can_manage_messages,  # noqa: F401
                     can_mention_everyone, can_react, can_upload)
from .datastructures import BigIntDict  # noqa: F401
from .datetime import assumed_utc, strpduration, utcnow  # noqa: F401
from .events import (DeleteResponder, EmoteResponder, Responder,  # noqa: F401
                     emote_added, emote_matches, emote_no_bots, event_filter,
                     run_responders, start_responders)
from .markdown import (E, a, arrow, blockquote, code, em,  # noqa: F401
                       iter_urls, pre, redact, sized, strike, strong, tag,
                       tag_literal, timestamp, traffic_light, u, unmarked,
                       untagged, unwrap_codeblock, urlqueryset, verbatim)
from .message import attachment_is_type, is_direct_message  # noqa: F401
from .pagination import (EmbedPagination, ParagraphStream,  # noqa: F401
                         TextPagination, chapterize, chapterize_fields,
                         chapterize_items, trunc_for_field)
from .response import ResponseInit  # noqa: F401
