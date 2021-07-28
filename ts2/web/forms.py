# forms.py
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

from operator import itemgetter

from django import forms

from ts2.discord.apps import DiscordBotConfig
from ts2.discord.models import Server

from .models import BugReport


class UserCreationForm(forms.Form):
    username = forms.CharField()
    snowflake = forms.IntegerField()

    access_token = forms.CharField()
    refresh_token = forms.CharField()
    expires_at = forms.IntegerField()

    handoff = forms.CharField(required=False)

    @property
    def itemgetter(self) -> itemgetter:
        return itemgetter(*self.fields.keys())

    def to_tuple(self):
        return self.itemgetter(self.cleaned_data)


class ServerCreationForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ['snowflake', 'invited_by', 'disabled']


    def save(self, *args, **kwargs):
        server = super().save(*args, **kwargs)

        apps = DiscordBotConfig.get()
        thread = apps.bot_thread

        async def sync_models(bot):
            try:
                guild = await bot.fetch_guild(server.snowflake)
            except Exception as e:
                import logging
                logging.getLogger().error(e, exc_info=e)
            guild._channels = {c.id: c for c in await guild.fetch_channels()}
            await bot.sync_server(guild)

        thread.run_coroutine(sync_models(thread.client))
        return server


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = BugReport
        fields = ['user', 'topic', 'summary', 'path']
