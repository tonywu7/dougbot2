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

import simplejson as json
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import (DestroyModelMixin, ListModelMixin,
                                   RetrieveModelMixin)
from rest_framework.response import Response

from ts2.discord.apps import DiscordBotConfig
from ts2.discord.constraint import CommandCondition, CommandCriteria
from ts2.discord.models import (BotCommand, Channel, CommandConstraint, Role,
                                Server)

from ..serializers import (BotCommandSerializer, ChannelSerializer,
                           CommandConstraintSerializer, RoleSerializer,
                           ServerDataSerializer)
from ..utils.http import HTTPBadRequest
from ..utils.views import DiscordServerModelListView


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
        if not req.user.is_superuser:
            app = DiscordBotConfig.get()
            thread = app.bot_thread
            bot = thread.client
            hidden = bot.manual.hidden_commands()
            queryset = self.queryset.exclude(identifier__in=hidden.keys()).all()
        else:
            queryset = self.queryset.all()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
