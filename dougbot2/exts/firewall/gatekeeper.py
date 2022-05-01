# gatekeeper.py
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

import logging

from asgiref.sync import sync_to_async
from discord import Message, Object, RawReactionActionEvent
from django.db import IntegrityError


class Gatekeeper:
    """Tool for screening incoming discord.py events against an entity blacklist.

    Used in the bot client to completely filter out events from certain
    guilds, roles, users, etc, such that the event won't be dispatched at all.
    """

    def __init__(self):
        from .models import Blacklisted
        self.log = logging.getLogger('discord.gatekeeper')
        self._query = Blacklisted.objects.values_list('snowflake', flat=True)

    @sync_to_async
    def add(self, obj: Object):
        """Add a Discord Object to the blacklist."""
        from .models import Blacklisted
        try:
            blacklisted = Blacklisted(snowflake=obj.id)
            blacklisted.save()
        except IntegrityError:
            return

    @sync_to_async
    def discard(self, obj: Object):
        """Remove a Discord Object from the blacklist."""
        from .models import Blacklisted
        try:
            blacklisted = Blacklisted.objects.get(snowflake=obj.id)
            blacklisted.delete()
        except Blacklisted.DoesNotExist:
            return

    async def match(self, *entities: Object) -> bool:
        """Find if any of the passed Discord Objects has its ID blacklisted.

        Return `True` if there is a match.
        """
        blacklisted = await self.blacklisted()
        return any(o.id in blacklisted for o in entities if o)

    @sync_to_async
    def blacklisted(self) -> set[int]:
        """Retrieve the set of blacklisted Discord IDs."""
        return set(self._query.all())

    async def on_message(self, message: Message):
        """Screen an `on_message` event.

        Return `True` any of the message, its guild, its channel, or its author
        has been blacklisted.
        """
        return not await self.match(message, message.guild, message.channel, message.author)

    async def on_reaction_add(self, reaction, member):
        """Screen an `on_reaction_add` event.

        Return `True` the member making the reaction is blacklisted.
        """
        return not await self.match(member)

    async def on_reaction_remove(self, reaction, member):
        """Screen an `on_reaction_remove` event.

        Return `True` the member removing the reaction is blacklisted.
        """
        return not await self.match(member)

    async def on_raw_reaction_add(self, evt: RawReactionActionEvent):
        """Screen an `on_raw_reaction_add` event.

        Return `True` any of the originating guild, channel,
        the message, or the user add the reaction is blacklisted.
        """
        entities = [Object(id_) for id_ in (evt.guild_id or 0, evt.channel_id or 0,
                                            evt.message_id, evt.user_id)]
        return not await self.match(*entities)

    async def on_raw_reaction_remove(self, evt: RawReactionActionEvent):
        """Screen an `on_raw_reaction_remove` event.

        Return `True` any of the originating guild, channel,
        the message, or the user removing the reaction is blacklisted.
        """
        entities = [Object(id_) for id_ in (evt.guild_id or 0, evt.channel_id or 0,
                                            evt.message_id, evt.user_id)]
        return not await self.match(*entities)

    async def handle(self, event_name: str, *args, **kwargs) -> bool:
        """Evaluate the event and return `True` if there is a match against the blacklist."""
        handler = getattr(self, f'on_{event_name}', None)
        if not handler:
            return True
        try:
            return await handler(*args, **kwargs)
        except Exception as e:
            self.log.error('Error while evaluating gatekeeper '
                           f'criteria for {event_name}', exc_info=e)
            return True
