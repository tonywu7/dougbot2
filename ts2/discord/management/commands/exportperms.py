# exportperms.py
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

from itertools import chain
from typing import TypedDict

import simplejson
from django.core.management.base import BaseCommand
from duckcord.permissions import Permissions2

from ...ext.autodoc.lang import readable_perm_name

L1 = Permissions2(
    administrator=True,
    manage_channels=True,
    manage_guild=True,
    view_audit_log=True,
)
L2 = Permissions2(
    manage_roles=True,
    manage_webhooks=True,
    manage_emojis=True,
)
L3 = Permissions2(
    view_guild_insights=True,
    kick_members=True,
    ban_members=True,
    mute_members=True,
    manage_nicknames=True,
)
L4 = Permissions2(
    priority_speaker=True,
    manage_messages=True,
    mention_everyone=True,
    deafen_members=True,
    move_members=True,
)
L5 = Permissions2(
    view_channel=True,
    send_messages=True,
    add_reactions=True,
    embed_links=True,
    attach_files=True,
    external_emojis=True,
    read_message_history=True,
    change_nickname=True,
    create_instant_invite=True,
    connect=True,
    speak=True,
    stream=True,
    use_voice_activation=True,
    send_tts_messages=True,
    request_to_speak=True,
    use_slash_commands=True,
)

COLORS = {
    L1: '#7acc9c',
    L2: '#ba6cd9',
    L3: '#6cadd9',
    L4: '#206694',
    L5: '#cf1f33',
}

COLOR_MAP: dict[str, str] = {}

for p, c in COLORS.items():
    for k in p:
        COLOR_MAP[k] = c


class PermItem(TypedDict):
    id: str
    content: str
    foreground: str


class Command(BaseCommand):
    help = 'Export keys and names of all supported Discord permissions to a JSON file.'

    requires_migrations_checks = []
    requires_system_checks = []

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '-o', '--output', action='store', dest='output',
            help='Destination file',
        )

    def handle(self, *args, output: str, **options):
        items: dict[str, PermItem] = {}
        for k in chain(L1, L2, L3, L4, L5):
            items[k] = {'content': readable_perm_name(k),
                        'foreground': COLOR_MAP[k]}
        with open(output, 'w+') as f:
            simplejson.dump(items, f)
