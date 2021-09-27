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
from typing import Optional, Union

from discord import (Emoji, File, Member, Message, PartialEmoji, Role,
                     StageChannel, TextChannel, User, VoiceChannel)
from discord.ext.commands import command
from PIL import Image, ImageColor

from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.utils.common import (Embed2, a, can_embed, can_upload, code,
                                      strong, timestamp)
from ts2.discord.utils.markdown import rgba2int

HEX_DIGITS = set(hexdigits)


def ishexdigit(s: str):
    return all(c in HEX_DIGITS for c in s)


class QueryCommands:
    @command('snowflake', aliases=('mtime',))
    @doc.description('Get the timestamp of a Discord snowflake (ID).')
    @doc.argument('snowflake', 'The snowflake to convert.')
    @can_embed
    # TODO: remove user
    async def snowflake(
        self, ctx: Circumstances, snowflake: Union[
            int, Member, Role, Message, TextChannel, User,
            VoiceChannel, StageChannel, Emoji, PartialEmoji,
        ],
    ):
        if not isinstance(snowflake, int):
            try:
                snowflake = snowflake.id
            except AttributeError:
                raise doc.NotAcceptable('Invalid argument.')
        epoch = 1420070400000 + (snowflake >> 22)
        try:
            dt = datetime.fromtimestamp(epoch / 1000, tz=timezone.utc)
        except ValueError:
            raise doc.NotAcceptable((
                'Timestamp out of range.'
                ' Make sure the argument provided is'
                ' indeed a Discord snowflake.'
            ))
        reps = [
            code(snowflake),
            code(epoch),
            code(dt.isoformat()),
            strong(timestamp(dt, 'full')),
            timestamp(dt, 'relative'),
        ]
        res = Embed2(title='Snowflake', description='\n'.join(reps))
        return await ctx.response(ctx, embed=res).reply().run()

    @command('color')
    @doc.description('Preview a color.')
    @doc.argument('color', (
        a('CSS color accepted by PIL,',
          'https://pillow.readthedocs.io/en/stable/reference/ImageColor.html#color-names')
        + ' such as a hex code.'
    ))
    @can_embed
    @can_upload
    async def color(self, ctx: Circumstances, *, color: Union[Role, str]):
        if isinstance(color, Role):
            color = f'#{color.color.value:06x}'
        if color[0] != '#' and ishexdigit(color):
            color = f'#{color}'
        try:
            r, g, b, *a = ImageColor.getrgb(color)
        except ValueError as e:
            raise doc.NotAcceptable(str(e))
        img = Image.new('RGBA', (32, 32), (r, g, b, *a))
        data = io.BytesIO()
        img.save(data, 'png')
        data.seek(0)
        f = File(data, 'color.png')
        a = a[0] if a else 255
        h, ll, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        hexcode = f'#{rgba2int(r, g, b, None):06x}'
        hexcode_alpha = f'#{rgba2int(r, g, b, a):08x}'
        h = 360 * h
        a = a / 255
        fmts = [
            strong(code(hexcode)),
            strong(code(hexcode_alpha)),
            f'rgba({r}, {g}, {b}, {a:.2f})',
            f'hsla({h:.1f}deg, {s:.1%}, {ll:.1%}, {a:.1f})',
        ]
        res = Embed2(description='\n'.join(fmts), color=rgba2int(r, g, b))
        return await ctx.response(ctx, embed=res, files=[f]).reply().deleter().run()

    @command('avatar', aliases=('pfp',))
    @doc.description("Get a user's avatar (profile pic).")
    @doc.argument('member', 'The user whose avatar to get.')
    @doc.invocation((), 'Get your profile pic.')
    @doc.invocation(('member',), "Get someone else's profile pic.")
    @can_embed
    async def avatar(self, ctx: Circumstances, member: Optional[Member]):
        if not member:
            member = ctx.author
        url = member.avatar_url_as()
        res = (Embed2(title='Avatar').personalized(member)
               .set_thumbnail(url=url)
               .set_description(code(url)))
        return await ctx.response(ctx, embed=res).deleter().run()
