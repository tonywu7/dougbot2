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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.template import TemplateDoesNotExist
from django.views.generic import View

from ts2.discord.middleware import optional_server_access

from ...models import Feature, PageInfo
from .forms import FeedbackForm
from .removal import rm


def index(req: HttpRequest) -> HttpResponse:
    return render(req, 'ts2/public/index.html')


@optional_server_access('read')
def feature_tracker(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'ts2/public/features.html', {
        'features': Feature.objects.order_by('status', 'ftype', 'name').all(),
        'pageinfo': PageInfo(description='Feature tracker'),
    })


class BugReportView(View):
    @staticmethod
    @login_required
    @optional_server_access('read')
    def get(req: HttpRequest, **kwargs) -> HttpResponse:
        return render(req, 'ts2/public/bugreport.html', {
            'endpoint': req.get_full_path(),
            'pageinfo': PageInfo(description='Bug report'),
        })

    @staticmethod
    @login_required
    @optional_server_access('read')
    def post(req: HttpRequest, **kwargs) -> HttpResponse:
        form = FeedbackForm({**req.POST.dict(), 'user': req.user})
        try:
            form.save()
        except Exception:
            status = 400
            messages.warning(req, 'Error while submitting bug report.')
        else:
            status = 201
            messages.success(req, 'Report submitted. Thank you!')
        return render(req, 'ts2/public/bugreport.html',
                      {'endpoint': req.get_full_path()}, status=status)


class InfoRemovalRequestView(View):
    @staticmethod
    @login_required
    @optional_server_access('read')
    def get(req: HttpRequest, **kwargs) -> HttpResponse:
        return render(req, 'ts2/public/removal.html', {
            'pageinfo': PageInfo(description='Data deletion request'),
        })

    @staticmethod
    @login_required
    @optional_server_access('read')
    def post(req: HttpRequest, **kwargs) -> HttpResponse:
        rm(req)
        return redirect('web:index')


@optional_server_access('read')
def blog(req: HttpRequest, dest: str, **kwargs) -> HttpResponse:
    try:
        return render(req, f'ts2/public/blog/{dest}.html')
    except TemplateDoesNotExist:
        raise Http404()
