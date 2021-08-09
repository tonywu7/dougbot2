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

from .models import Blacklisted


class Gatekeeper:
    def __init__(self):
        self.log = logging.getLogger('discord.gatekeeper')
        self._query = Blacklisted.objects.values_list('snowflake', flat=True)

    @sync_to_async
    def add(self, obj: Object):
        try:
            blacklisted = Blacklisted(snowflake=obj.id)
            blacklisted.save()
        except IntegrityError:
            return

    @sync_to_async
    def discard(self, obj: Object):
        try:
            blacklisted = Blacklisted.objects.get(snowflake=obj.id)
            blacklisted.delete()
        except Blacklisted.DoesNotExist:
            return

    async def match(self, *entities: Object) -> bool:
        blacklisted = await self.blacklisted()
        return any(o.id in blacklisted for o in entities if o)

    @sync_to_async
    def blacklisted(self) -> set[int]:
        return set(self._query.all())

    async def on_message(self, message: Message):
        return not await self.match(message, message.guild, message.channel, message.author)

    async def on_reaction_add(self, reaction, member):
        return not await self.match(member)

    async def on_reaction_remove(self, reaction, member):
        return not await self.match(member)

    async def on_raw_reaction_add(self, evt: RawReactionActionEvent):
        entities = [Object(id_) for id_ in (evt.guild_id or 0, evt.channel_id or 0,
                                            evt.message_id, evt.user_id)]
        return not await self.match(*entities)

    async def on_raw_reaction_remove(self, evt: RawReactionActionEvent):
        entities = [Object(id_) for id_ in (evt.guild_id or 0, evt.channel_id or 0,
                                            evt.message_id, evt.user_id)]
        return not await self.match(*entities)

    async def handle(self, event_name: str, *args, **kwargs) -> bool:
        handler = getattr(self, f'on_{event_name}', None)
        if not handler:
            return True
        try:
            return await handler(*args, **kwargs)
        except Exception as e:
            self.log.error('Error while evaluating gatekeeper '
                           f'criteria for {event_name}', exc_info=e)
            return True
