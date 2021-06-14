# data.py
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

from typing import Type

from django.core.exceptions import SuspiciousOperation
from django.http import HttpRequest, HttpResponse
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin,
                                   ListModelMixin, RetrieveModelMixin,
                                   UpdateModelMixin)
from rest_framework.serializers import ModelSerializer

from telescope2.discord.models import (BotCommand, Channel, CommandConstraint,
                                       Role, ServerScoped)

from ..contexts import DiscordContext
from ..serializers import (BotCommandSerializer, ChannelSerializer,
                           CommandConstraintSerializer, RoleSerializer)


class DiscordServerModelListView(ListModelMixin, GenericAPIView):
    model: Type[ServerScoped]
    serializer_class: Type[ModelSerializer]

    @property
    def queryset(self):
        try:
            ctx: DiscordContext = self.request.discord
        except AttributeError:
            raise SuspiciousOperation('Invalid parameters.')
        return self.model.objects.filter(guild_id__exact=ctx.prefs.snowflake)

    def get(self, req: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.list(req, *args, **kwargs)


class ChannelListView(DiscordServerModelListView):
    model = Channel
    serializer_class = ChannelSerializer


class RoleListView(DiscordServerModelListView):
    model = Role
    serializer_class = RoleSerializer


class CommandConstraintListView(CreateModelMixin, DiscordServerModelListView):
    model = CommandConstraint
    serializer_class = CommandConstraintSerializer

    def post(self, req, *args, **kwargs):
        return self.create(req, *args, **kwargs)


class CommandConstraintDetailsView(
    RetrieveModelMixin, UpdateModelMixin,
    DestroyModelMixin, GenericAPIView,
):
    model = CommandConstraint
    serializer_class = CommandConstraintSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class BotCommandListView(ListModelMixin, GenericAPIView):
    queryset = BotCommand.objects.all()
    serializer_class = BotCommandSerializer

    def get(self, req: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.list(req, *args, **kwargs)
