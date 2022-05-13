# bot.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

from discord import Message, MessageReference, RawMessageDeleteEvent

from dougbot2.discord import Gear


class ReplyUtils(
    Gear,
    name="Reply utilities",
    order=99,
    description="",
):
    @Gear.listener("on_message")
    async def on_bot_reply(self, msg: Message):
        """Implement a listener that auto-deletes the bot's replies to commands.

        Listen to message delete events. If the bot has replied to the deleted message,
        delete the reply as well to reduce clutter.

        Does not always succeed. Relies on the reply being found in the redis cache.
        """
        bot = self.bot
        if msg.author != bot.user:
            return
        ref: MessageReference = msg.reference
        if not ref or not ref.cached_message:
            return
        referrer: Message = ref.cached_message
        bot.set_cache(msg.id, 31536000, referrer=referrer.id)

    @Gear.listener("on_raw_message_delete")
    async def on_command_call_delete(self, ev: RawMessageDeleteEvent):
        bot = self.bot
        channel = bot.get_channel(ev.channel_id)
        if not channel:
            return
        referred = bot.get_cache(None, referrer=ev.message_id)
        if referred is None:
            return
        bot.del_cache(referrer=ev.message_id)
        msg = channel.get_partial_message(referred)
        await msg.delete(delay=0)
