# queries.py
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

import colorsys
import io
from datetime import datetime, timezone
from string import hexdigits
from typing import Literal, Optional, Union

from PIL import Image, ImageColor
from discord import (
    Emoji,
    File,
    Guild,
    Member,
    Message,
    PartialEmoji,
    Role,
    StageChannel,
    TextChannel,
    VoiceChannel,
)
from discord.ext.commands import command

from dougbot2.blueprints import Surroundings
from dougbot2.exceptions import NotAcceptable
from dougbot2.exts import autodoc as doc
from dougbot2.utils.common import (
    Embed2,
    a,
    can_embed,
    can_upload,
    code,
    strong,
    timestamp,
)
from dougbot2.utils.converters import Choice
from dougbot2.utils.markdown import rgba2int

HEX_DIGITS = set(hexdigits)


def is_hex_digit(s: str):
    """Check if this string is a valid hexadecimal number."""
    return all(c in HEX_DIGITS for c in s)


class QueryCommands:
    """Commands for getting details about some Discord data."""

    @command("snowflake", aliases=("mtime",))
    @doc.description("Get the timestamp of a Discord snowflake (ID).")
    @doc.argument("snowflake", "The snowflake to convert.")
    @can_embed
    async def snowflake(
        self,
        ctx: Surroundings,
        snowflake: Union[
            int,
            Member,
            Role,
            Message,
            TextChannel,
            VoiceChannel,
            StageChannel,
            Emoji,
            PartialEmoji,
        ],
    ):
        if not isinstance(snowflake, int):
            try:
                snowflake = snowflake.id
            except AttributeError:
                raise doc.NotAcceptable("Invalid argument.")
        epoch = 1420070400000 + (snowflake >> 22)
        try:
            dt = datetime.fromtimestamp(epoch / 1000, tz=timezone.utc)
        except ValueError:
            raise NotAcceptable(
                (
                    "Timestamp out of range."
                    " Make sure the argument provided is"
                    " indeed a Discord snowflake."
                )
            )
        reps = [
            code(snowflake),
            code(epoch),
            code(dt.isoformat()),
            strong(timestamp(dt, "full")),
            timestamp(dt, "relative"),
        ]
        res = Embed2(title="Snowflake", description="\n".join(reps))
        return await ctx.respond(embed=res).reply().run()

    @command("color")
    @doc.description("Preview a color.")
    @doc.argument(
        "color",
        (
            a(
                "CSS color accepted by PIL,",
                "https://pillow.readthedocs.io/en/stable/reference/ImageColor.html#color-names",
            )
            + " such as a hex code, or a server role with color."
        ),
    )
    @can_embed
    @can_upload
    async def color(self, ctx: Surroundings, *, color: Union[Role, str]):
        if isinstance(color, Role):
            color = f"#{color.color.value:06x}"
        if color[0] != "#" and is_hex_digit(color):
            color = f"#{color}"
        try:
            r, g, b, *a = ImageColor.getrgb(color)
        except ValueError as e:
            raise doc.NotAcceptable(str(e))
        img = Image.new("RGBA", (32, 32), (r, g, b, *a))
        data = io.BytesIO()
        img.save(data, "png")
        data.seek(0)
        f = File(data, "color.png")
        a = a[0] if a else 255
        h, ll, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        hexcode = f"#{rgba2int(r, g, b, None):06x}"
        hexcode_alpha = f"#{rgba2int(r, g, b, a):08x}"
        h = 360 * h
        a = a / 255
        results = [
            strong(code(hexcode)),
            strong(code(hexcode_alpha)),
            f"rgba({r}, {g}, {b}, {a:.2f})",
            f"hsla({h:.1f}deg, {s:.1%}, {ll:.1%}, {a:.1f})",
        ]
        res = Embed2(description="\n".join(results), color=rgba2int(r, g, b))
        return await ctx.respond(embed=res, files=[f]).reply().deleter().run()

    @command("asset", aliases=("cdn",))
    @doc.description("Get the CDN URL of a Discord asset (e.g. avatars, emotes)")
    @doc.invocation(("target",), None)
    @can_embed
    async def cdn(
        self,
        ctx: Surroundings,
        target: Union[Member, Guild, Emoji, PartialEmoji],
        filetype: Optional[Choice[Literal["webp", "png", "jpg"]]] = "png",
    ):
        if isinstance(target, Member):
            asset = target.avatar_url_as(static_format=filetype)
            name = "Profile picture"
            description = target.mention
        elif isinstance(target, Guild):
            asset = target.icon_url_as(static_format=filetype)
            name = "Server icon"
            description = target.name
        elif isinstance(target, (Emoji, PartialEmoji)):
            asset = target.url_as(static_format=filetype)
            name = "Emote"
            description = f"{target} {code(target)}"
        res = (
            Embed2(title=name)
            .set_thumbnail(url=asset)
            .set_description(f"{strong(description)}\n{a(asset, asset)}")
        )
        return await ctx.respond(embed=res).deleter().run()
