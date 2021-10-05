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

import asyncio
import threading

from discord.ext.commands import command

from ts2.conf.versions import list_versions
from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.utils.common import Embed2, EmbedField, code


class Measurement(
    Gear, name='Measurement', order=60,
    description='Metrics & inspection',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('runtime')
    @doc.description("Show the bot's runtime status.")
    async def runtime(self, ctx: Circumstances):
        versions = ' '.join([code(f'{pkg}/{v}') for pkg, v
                             in list_versions().items()])
        num_servers = len(self.bot.guilds)
        num_channels = len([*self.bot.get_all_channels()])
        num_members = len([*self.bot.get_all_members()])
        num_dms = len(self.bot.private_channels)
        threads = threading.enumerate()
        tasks = [t for t in asyncio.all_tasks() if not t.done()]
        info = [
            EmbedField('Servers/Members', f'{num_servers}/{num_members}'),
            EmbedField('Channels/DMs', f'{num_channels}/{num_dms}'),
            EmbedField('Versions', versions, False),
            EmbedField('Threads/Coroutines', f'{len(threads)}/{len(tasks)}'),
        ]
        res = (
            Embed2(title='Bot status', fields=info)
            .set_timestamp()
            .personalized(ctx.guild.me)
        )
        return await ctx.reply(embed=res)
