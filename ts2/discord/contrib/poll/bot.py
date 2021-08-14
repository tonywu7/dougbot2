# bot.py
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

from typing import Union

from discord import Emoji, Guild, PartialEmoji, TextChannel
from discord.ext.commands import command, group

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.utils.async_ import async_get, async_list
from ts2.discord.utils.common import Embed2, tag

from .models import SuggestionChannel

EmoteType = Union[Emoji, PartialEmoji, str]


class Poll(
    Gear, name='Poll', order=20,
    description='Suggestions & polls',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def list_suggest_channels(self, guild: Guild) -> str:
        channels = {c.id: c for c in guild.channels}
        q = SuggestionChannel.objects.filter(channel_id__in=channels)
        lines = []
        for c in await async_list(q):
            c: SuggestionChannel
            lines.append(tag(channels[c.channel_id]))
            if c.description:
                lines.append(c.description)
        return '\n'.join(lines).strip()

    async def get_channel_or_404(self, ctx: Circumstances, channel: TextChannel):
        channels = [c.id for c in ctx.guild.channels]
        suggests = SuggestionChannel.objects.filter(channel_id__in=channels)
        try:
            suggest: SuggestionChannel = await async_get(suggests, channel_id=channel.id)
        except SuggestionChannel.DoesNotExist:
            raise doc.NotAcceptable((f'{tag(channel)} is not a suggestion channel.'))
        else:
            return suggest

    @command('suggest')
    @doc.description('Make a suggestion.')
    @doc.argument('category', 'The suggestion channel to use.')
    @doc.argument('suggestion', 'Your suggestion here.')
    async def suggest(
        self, ctx: Circumstances,
        category: TextChannel,
        *, suggestion: str = '',
    ):
        target = await self.get_channel_or_404(ctx, category)
        return await ctx.send(target)

    @group('suggest-channel', invoke_without_command=True)
    @doc.description('List all suggestion channels.')
    @doc.hidden
    async def suggest_channels(self, ctx: Circumstances):
        channel_list = await self.list_suggest_channels(ctx.guild)
        if not channel_list:
            channel_list = '(no suggest channels)'
        res = (Embed2(title='Suggestion channels', description=channel_list)
               .decorated(ctx.guild))
        return await ctx.response(ctx, embed=res).reply().deleter().run()
