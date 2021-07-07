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

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.generic import View

from ts2.discord.apps import DiscordBotConfig
from ts2.discord.logging import PRIVILEGED_EXCEPTIONS

from ..config import CommandAppConfig
from ..contexts import DiscordContext
from ..forms import LoggingConfigFormset, ModelSyncActionForm
from ..models import write_access_required
from .mutation import error_response

Extensions = dict[str, CommandAppConfig]


@login_required
@write_access_required
def index(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'telescope2/web/manage/index.html')


@login_required
@write_access_required
def core(req: HttpRequest, **kwargs) -> HttpResponse:
    current_user = req.user
    ctx: DiscordContext = req.get_ctx()
    server_invited_by = ctx.server.invited_by
    if (server_invited_by is not None
            and server_invited_by == current_user
            or server_invited_by is None):
        access_control = True
    else:
        access_control = False
    return render(req, 'telescope2/web/manage/core.html',
                  context={'access_control': access_control})


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


@require_POST
@login_required
@write_access_required
@user_passes_test(lambda u: u.is_superuser)
def model_synchronization_view(req: HttpRequest, guild_id: str) -> HttpResponse:
    item = get_object_or_404(ModelSyncActionForm._meta.model, pk=guild_id)
    form = ModelSyncActionForm(data=req.POST, instance=item)

    if not form.is_valid():
        return error_response(form.errors)

    app = DiscordBotConfig.get()
    thread = app.bot_thread

    async def task(bot):
        guild = await bot.fetch_guild(form.cleaned_data['snowflake'])
        guild._channels = {c.id: c for c in await guild.fetch_channels()}
        guild._roles = {r.id: r for r in await guild.fetch_roles()}
        await bot.sync_server(guild)

    thread.run_coroutine(task(thread.client))

    messages.info(req, 'Models synchronized.', extra_tags='success')
    return redirect(reverse('web:manage.core', kwargs={'guild_id': guild_id}))
