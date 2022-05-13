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

from asgiref.sync import sync_to_async
from discord import Message

from dougbot2.discord import Gear
from dougbot2.models import Server
from dougbot2.utils.dm import is_direct_message
from dougbot2.utils.markdown import strong


class Summon(Gear, name="Summon", order=200, description="", hidden=True):
    @sync_to_async
    def get_prefix(self, guild_id: int) -> str:
        return Server.objects.get(snowflake=guild_id).prefix

    @Gear.listener("on_message")
    async def on_bare_mention(self, msg: Message):
        """Reply with the bot's prefix in this server if the bot is mentioned without anything else."""
        bot = self.bot
        if is_direct_message(msg):
            return
        if msg.content == f"<@!{bot.user.id}>":
            prefix = await self.get_prefix(msg.guild.id)
            example = f"{prefix}echo"
            return await msg.reply(
                f"Prefix is {strong(prefix)}\nExample command: {strong(example)}"
            )
