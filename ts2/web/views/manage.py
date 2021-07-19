# manage.py
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

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from ts2.discord.apps import DiscordBotConfig

from ..middleware import get_ctx
from ..models import write_access_required


@login_required
@write_access_required
def index(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'telescope2/web/manage/index.html')


@login_required
@write_access_required
def core(req: HttpRequest, **kwargs) -> HttpResponse:
    current_user = req.user
    ctx = get_ctx(req)
    server_invited_by = ctx.server.invited_by
    if (server_invited_by is not None
            and server_invited_by == current_user
            or server_invited_by is None):
        access_control = True
    else:
        access_control = False

    enabled = ctx.server.extensions
    exts = [(app.label, app.icon_and_title, app.label in enabled) for app
            in DiscordBotConfig.ext_map.values()]

    return render(
        req, 'telescope2/web/manage/core.html',
        context={
            'access_control': access_control,
            'extensions': exts,
        },
    )


@login_required
@write_access_required
def constraints(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'telescope2/web/manage/constraints.html')


@login_required
@write_access_required
def logging_config(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'telescope2/web/manage/logging.html')
