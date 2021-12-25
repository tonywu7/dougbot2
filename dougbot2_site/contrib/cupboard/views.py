# views.py
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

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, HttpRequest
from django.shortcuts import get_object_or_404

from ts2.discord.middleware import require_server_access
from ts2.web.models import per_user_access

from .models import ServerResource


@login_required
@require_server_access('read')
@per_user_access
def get_server_resource(req: HttpRequest, guild_id: str, target: str):
    path = ServerResource.server_prefixed_path(guild_id, target)
    upload = get_object_or_404(ServerResource, upload=path)
    return FileResponse(upload.upload.open('rb'))
