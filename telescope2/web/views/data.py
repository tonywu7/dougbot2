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

import simplejson as json
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (
    CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.serializers import ModelSerializer

from telescope2.discord.constraint import CommandCondition, CommandCriteria
from telescope2.discord.models import (
    BotCommand, Channel, CommandConstraint, CommandConstraintList, Role,
    Server, ServerScoped,
)

from ..contexts import DiscordContext
from ..serializers import (
    BotCommandSerializer, ChannelSerializer, CommandConstraintListSerializer,
    CommandConstraintSerializer, RoleSerializer, ServerDataSerializer,
)
from ..utils.http import HTTPBadRequest


class DiscordServerModelListView(ListModelMixin, GenericAPIView):
    model: Type[ServerScoped]
    serializer_class: Type[ModelSerializer]

    @property
    def queryset(self):
        ctx: DiscordContext = self.request.get_ctx()
        return self.model.objects.filter(guild_id__exact=ctx.server.snowflake)

    def get(self, req: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.list(req, *args, **kwargs)


class ChannelListView(DiscordServerModelListView):
    model = Channel
    serializer_class = ChannelSerializer


class RoleListView(DiscordServerModelListView):
    model = Role
    serializer_class = RoleSerializer


class ServerDataView(RetrieveModelMixin, GenericAPIView):
    queryset = Server.objects.all()
    serializer_class = ServerDataSerializer
    lookup_url_kwarg = 'guild_id'

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class BotCommandListView(ListModelMixin, GenericAPIView):
    queryset = BotCommand.objects.all()
    serializer_class = BotCommandSerializer

    def get(self, req: HttpRequest, *args, **kwargs) -> HttpResponse:
        return self.list(req, *args, **kwargs)


class CommandConstraintListView(
    CreateModelMixin, RetrieveModelMixin,
    UpdateModelMixin, DiscordServerModelListView,
):
    model = CommandConstraintList
    serializer_class = CommandConstraintListSerializer
    lookup_url_kwarg = 'guild_id'

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class CommandConstraintDetailsView(
    RetrieveModelMixin, DestroyModelMixin, GenericAPIView,
):
    queryset = CommandConstraint.objects.all()
    serializer_class = CommandConstraintSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


@csrf_exempt
@require_POST
def constraint_test(req: HttpRequest) -> HttpResponse:
    try:
        data = json.loads(req.body.decode('utf8'))
        config = data['config']
        constraints = config['constraints']
        channel_id = int(data['channel'][0])
        command_id = int(data['command'][0])
        roles = {int(r) for r in data['roles']}
    except (json.JSONDecodeError, ValueError, LookupError):
        return HTTPBadRequest()

    conditions = [CommandCondition.deserialize(d) for d in constraints]
    conditions = [c for c in conditions if (
        (channel_id in c.channels or not c.channels)
        and (command_id in c.commands or not c.commands)
    )]
    criteria = CommandCriteria(conditions)

    return JsonResponse({'result': criteria.test(roles) is True})
