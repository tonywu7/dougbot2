# updater.py
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

"""Passive Discord gateway receiver."""

from discord import Intents

from .apps import no_credentials
from .bot import Robot
from .runner import BotRunner

updater_thread: BotRunner[Robot] = None


def get_updater():
    global updater_thread
    if updater_thread is None:
        if no_credentials():
            raise ValueError('Discord credentials are missing.')
        config = {
            'intents': Intents(guilds=True, members=True),
        }
        updater_thread = BotRunner(Robot, config, listen=True, daemon=True)
        updater_thread.start()
    with updater_thread.connect:
        updater_thread.connect.wait_for(updater_thread.connected)
    return updater_thread
