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

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render

from .bot import Telescope


@login_required
@permission_required(['discord.manage_servers'])
def authorized(req: HttpRequest) -> HttpResponse:
    return HttpResponse(content=req.body.decode('utf8'))


def invite(req: HttpRequest) -> HttpResponse:
    return HttpResponseRedirect(Telescope.build_oauth2_url(req), status=307)


def index(req: HttpRequest) -> HttpResponse:
    if not Telescope.is_alive:
        Telescope.run()
    return render(req, 'bot/index.html')
