# checks.py
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

from discord.ext.commands import bot_has_permissions


def can_embed(f):
    return bot_has_permissions(embed_links=True)(f)


def can_upload(f):
    return bot_has_permissions(attach_files=True)(f)


def can_manage_messages(f):
    return bot_has_permissions(manage_messages=True)(f)


def can_react(f):
    return bot_has_permissions(add_reactions=True)(f)


def can_mention_everyone(f):
    return bot_has_permissions(mention_everyone=True)(f)
