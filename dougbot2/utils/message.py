# message.py
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

import mimetypes
from fnmatch import fnmatch
from typing import Optional, Union

from discord import Attachment, DMChannel, GroupChannel, Message, TextChannel
from discord.ext.commands import Context


def attachment_is_type(att: Attachment, test: str) -> bool:
    """Check if the attachment is of a certain MIME type.

    If the Content-Type attribute is missing on the Attachment object,
    it uses `mimetypes` to guess the content type.

    Supports wildcard matching (via `fnmatch`; similar to the
    HTTP `Accept` field).
    """
    contenttype: Optional[str] = att.content_type
    if not contenttype:
        contenttype, encoding = mimetypes.guess_type(att.url, False)
    return contenttype and fnmatch(contenttype, test)


def is_direct_message(ctx: Union[Message, Context, TextChannel]):
    """Check if the context is in a DM context.

    The context may be a Context, Message, or TextChannel object.
    """
    cls = (DMChannel, GroupChannel)
    return isinstance(ctx, cls) or isinstance(getattr(ctx, "channel", None), cls)
