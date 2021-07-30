# threading.py
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

from discord import Intents

from .apps import no_credentials
from .bot import Robot
from .runner import BotRunner

client_thread: BotRunner[Robot] = None


def get_thread():
    global client_thread
    if client_thread is None:
        if no_credentials():
            raise ValueError('Discord credentials are missing.')
        client_thread = BotRunner(
            Robot, {'intents': Intents(guilds=True, members=True)},
            listen=True, daemon=True,
        )
        client_thread.start()
    with client_thread.bot_init:
        client_thread.bot_init.wait_for(client_thread.bot_initialized)
    return client_thread
