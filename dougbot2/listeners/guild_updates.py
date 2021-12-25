# updates.py
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

from discord import Guild
from discord.ext.commands import Cog

from ...apps import server_allowed
from ...server import sync_server


class Listener(Cog):
    def __init__(self):
        self.log = logging.getLogger('discord.guild_updates')

    @Cog.listener('on_guild_join')
    async def on_guild_join(self, guild: Guild):
        """Check if this guild has been whitelisted for the program upon joining.

        If it is not, leave immediately.
        """
        self.log.info(f'Joined {guild}')
        if not server_allowed(guild.id):
            self.log.warning(f'{guild} is not in the list of allowed guilds!')
            return await guild.leave()

    @Cog.listener('on_guild_channel_create')
    @Cog.listener('on_guild_channel_update')
    @Cog.listener('on_guild_channel_delete')
    async def update_channels(self, channel, updated=None):
        """Synchronize guild channels to the database."""
        updated = updated or channel
        await sync_server(updated.guild, info=False, roles=False)
        self.log.debug(f'Updated channels for {updated.guild}; reason: {repr(updated)}')

    @Cog.listener('on_guild_role_create')
    @Cog.listener('on_guild_role_update')
    @Cog.listener('on_guild_role_delete')
    async def update_roles(self, role, updated=None):
        """Synchronize guild roles to the database."""
        updated = updated or role
        await sync_server(role.guild, info=False, channels=False)
        self.log.debug(f'Updated roles for {updated.guild}; reason: {repr(updated)}')

    @Cog.listener('on_guild_update')
    async def update_server(self, before: Guild, after: Guild):
        """Synchronize guild details to the database."""
        await sync_server(after, roles=False, channels=False, layout=False)
        self.log.debug(f'Updated server info for {after}; reason: {repr(after)}')

    @Cog.listener('on_guild_available')
    async def update_server_initial(self, guild: Guild):
        """Run synchronization when the bot reconnects to a guild."""
        if not server_allowed(guild.id):
            self.log.warning(f'{guild} is not in the list of allowed guilds!')
            return await guild.leave()
        await sync_server(guild)
