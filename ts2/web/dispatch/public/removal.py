# removal.py
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

from asgiref.sync import async_to_sync
from django.apps import apps
from django.contrib.auth import logout
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest

from ts2.discord.fetch import DiscordFetch, create_session

from ...models import User


def revoke(req: HttpRequest):
    if req.user.is_anonymous:
        return
    user: User = req.user

    @async_to_sync
    async def do_revoke():
        fetch = DiscordFetch(create_session())
        return await fetch.revoke_token(user.refresh_token)

    do_revoke()


def rm(req: HttpRequest):
    if req.user.is_anonymous:
        return
    user_id = req.user.pk
    revoke(req)
    logout(req)
    for m in apps.get_models():
        try:
            ident = m.objects.get(pk=user_id)
            ident.delete()
        except ObjectDoesNotExist:
            continue
