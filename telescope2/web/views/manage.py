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

from typing import Dict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View

from telescope2.discord.logging import PRIVILEGED_EXCEPTIONS

from ..config import CommandAppConfig
from ..contexts import DiscordContext
from ..forms import LoggingConfigFormset
from ..models import write_access_required

Extensions = Dict[str, CommandAppConfig]


@login_required
@write_access_required
def index(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'telescope2/web/manage/index.html')


@login_required
@write_access_required
def core(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'telescope2/web/manage/core.html')


@login_required
@write_access_required
def constraints(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'telescope2/web/manage/constraints.html')


@method_decorator(login_required, 'dispatch')
@method_decorator(write_access_required, 'dispatch')
class LoggingConfigView(View):
    def get(self, req: HttpRequest, **kwargs) -> HttpResponse:
        ctx: DiscordContext = req.get_ctx()
        formset = ctx.forms.logging()
        return render(req, 'telescope2/web/manage/logging.html', {'formset': formset})

    def post(self, req: HttpRequest, **kwargs) -> HttpResponse:
        ctx: DiscordContext = req.get_ctx()
        formset = LoggingConfigFormset(data=req.POST)
        context = {
            'formset': formset,
        }
        if not formset.is_valid():
            context['errors'] = True
        else:
            for form in formset:
                if (form.cleaned_data['key'] in PRIVILEGED_EXCEPTIONS
                        and not req.user.is_superuser):
                    raise PermissionDenied()
            formset.save(ctx.server)
        return render(req, 'telescope2/web/manage/logging.html', context)
