# utils.py
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

from contextlib import suppress
from typing import Union

from discord import DMChannel, GroupChannel, Message, TextChannel
from discord.ext.commands import Context
from discord.ext.commands.view import StringView

from ...utils.english import pl_cat_attributive, readable_perm_name
from ...utils.markdown import strong, tag_literal


def format_roles(roles: list[int]):
    return pl_cat_attributive(
        "role", [tag_literal("role", r) for r in roles], conj="or"
    )


def format_permissions(perms: list[str]):
    return pl_cat_attributive(
        "permission", [strong(readable_perm_name(p)) for p in perms]
    )


def is_direct_message(ctx: Union[Message, Context, TextChannel]):
    """Check if the context is in a DM context.

    The context may be a Context, Message, or TextChannel object.
    """
    cls = (DMChannel, GroupChannel)
    return isinstance(ctx, cls) or isinstance(getattr(ctx, "channel", None), cls)


def full_invoked_with(ctx: Context) -> str:
    """The fully-qualified sequence of command names that has been parsed."""
    return " ".join(
        {**{k: True for k in ctx.invoked_parents}, ctx.invoked_with: True}.keys()
    )


def indicate_eol(ctx: Context) -> str:
    """Indicate the end of line of a discord.py StringView."""
    s = ctx.view
    return f"{s.buffer[:s.index + 1]} ←"


def indicate_this_arg(ctx: Context, argname: str = "...", truncate: int = 128) -> str:
    """Indicate the portion of a StringView that is currently being parsed."""
    s: StringView = ctx.view
    index = s.index
    previous = s.previous
    s.undo()
    with suppress(Exception):
        pending = s.get_quoted_word()
    if not pending:
        pending = s.buffer[index:]
    if not pending:
        pending = f"[{argname}]"
    s.index = index
    s.previous = previous
    if truncate and len(pending) > truncate:
        pending = f"{pending[:truncate]} ... (shortened)"
    return f"{s.buffer[:previous]} → {pending} ←"


def indicate_next_arg(ctx: Context, argname: str = "...", truncate: int = 128) -> str:
    """Indicate the portion of a StringView that has not been parsed."""
    s: StringView = ctx.view
    index = s.index
    previous = s.previous
    with suppress(Exception):
        pending = s.get_quoted_word()
    if not pending:
        pending = s.buffer[index:]
    if not pending:
        pending = f"[{argname}]"
    s.index = index
    s.previous = previous
    if truncate and len(pending) > truncate:
        pending = f"{pending[:truncate]} ... (shortened)"
    return f"{s.buffer[:s.index]} → {pending} ←"
