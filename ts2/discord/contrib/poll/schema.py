# schema.py
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

from graphene import (ID, Argument, Boolean, InputObjectType, Int, List,
                      Mutation, NonNull, ObjectType, String)
from graphene_django import DjangoObjectType

from ts2.discord.middleware import (get_server_scoped_model,
                                    intersect_server_model)
from ts2.discord.models import Channel
from ts2.discord.utils.common import BigIntDict
from ts2.discord.utils.graphql import (HasContext, KeyValuePairInput,
                                       KeyValuePairType)

from .models import SuggestionChannel


class SuggestionChannelType(DjangoObjectType):
    channel_id = ID(required=True)

    arbiters = List(NonNull(ID), required=True)
    reactions = List(NonNull(KeyValuePairType), required=True)

    class Meta:
        model = SuggestionChannel
        fields = [
            'title', 'description',
            'upvote', 'downvote',
            'requires_text',
            'requires_uploads',
            'requires_links',
        ]

    @classmethod
    def resolve_reactions(cls, root: SuggestionChannel, *args, **kwargs):
        return KeyValuePairType.from_dict(root.reactions)


class SuggestionChannelInput(InputObjectType):
    channel_id = Argument(ID, required=True)
    title = Argument(String, required=True)
    description = Argument(String, required=True)
    upvote = Argument(String, required=True)
    downvote = Argument(String, required=True)
    requires_text = Argument(Boolean, required=True)
    requires_uploads = Argument(Int, required=True)
    requires_links = Argument(Int, required=True)
    arbiters = List(NonNull(ID), required=True)
    reactions = List(NonNull(KeyValuePairInput), required=True)

    def mutate(self, obj: SuggestionChannel):
        for key in obj.updatable_fields:
            setattr(obj, key, getattr(self, key))
        obj.reactions = KeyValuePairInput.to_dict(self.reactions)

    def new(self, server_id: int) -> SuggestionChannel:
        channel = SuggestionChannel()
        self.mutate(channel)
        channel.channel_id = self.channel_id
        channel.server_id = server_id
        return channel


class SuggestionChannelUpdateMutation(Mutation):
    channels = List(SuggestionChannelType)

    class Arguments:
        server_id = Argument(ID, required=True)
        channels = Argument(List(SuggestionChannelInput), default_value=())

    @classmethod
    def mutate(cls, root, info: HasContext, *, server_id: str, channels: list[SuggestionChannelInput]):
        channel_map = BigIntDict({c.channel_id: c for c in channels})
        to_update = get_server_scoped_model(info.context, SuggestionChannel.channel, server_id, 'write')
        for channel in list(to_update):
            change = channel_map.pop(channel.channel_id, None)
            if not change:
                continue
            change.mutate(channel)
        to_create = [c.new(server_id) for c in channel_map.values()]
        to_create = {c.channel_id: c for c in to_create}
        to_create = intersect_server_model(to_create, server_id, Channel).values()
        SuggestionChannel.objects.bulk_create(to_create)
        SuggestionChannel.objects.bulk_update(to_update, SuggestionChannel.updatable_fields)
        return cls([*to_update, *to_create])


class SuggestionChannelDeleteMutation(Mutation):
    successful = Boolean(required=True)

    class Arguments:
        server_id = Argument(ID, required=True)
        channel_ids = Argument(List(ID), default_value=())

    @classmethod
    def mutate(cls, root, info: HasContext, *, server_id: str, channel_ids: list[str]):
        get_server_scoped_model(
            info.context, SuggestionChannel.channel,
            server_id, 'write', channel_id__in=channel_ids,
        ).delete()
        return cls(True)


class PollQuery(ObjectType):
    suggest_channels = List(SuggestionChannelType, server_id=ID(required=True))

    @classmethod
    def resolve_suggest_channels(cls, root, info: HasContext, server_id: str):
        return get_server_scoped_model(info.context, SuggestionChannel.channel, server_id, 'read')


class PollMutation(ObjectType):
    update_suggest_channels = SuggestionChannelUpdateMutation.Field()
    delete_suggest_channels = SuggestionChannelDeleteMutation.Field()
