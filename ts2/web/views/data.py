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

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin

from ts2.discord.models import Channel, Role, Server

from ..serializers import (ChannelSerializer, RoleSerializer,
                           ServerDataSerializer)
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
