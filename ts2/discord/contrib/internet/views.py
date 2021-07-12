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

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin,
                                   RetrieveModelMixin, UpdateModelMixin)

from ts2.web.utils.views import DiscordServerModelListView

from .models import RoleTimezone
from .serializers import RoleTimezoneSerializer


async def timezone_index(req: HttpRequest, **kwargs) -> HttpResponse:
    return render(req, 'ts2/discord/contrib/internet/timeanddate.html')


class RoleTimezoneView(
    RetrieveModelMixin, CreateModelMixin,
    UpdateModelMixin, DestroyModelMixin,
    GenericAPIView,
):
    model = RoleTimezone
    serializer_class = RoleTimezoneSerializer
    queryset = RoleTimezone.objects.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class RoleTimezoneListView(DiscordServerModelListView):
    model = RoleTimezone
    serializer_class = RoleTimezoneSerializer

    @property
    def queryset(self):
        return self.model.objects.filter(role__guild_id__exact=self.kwargs['guild_id'])

    def get(self, req: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.list(req, *args, **kwargs)
