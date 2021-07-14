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

from asgiref.sync import async_to_sync
from django import forms
from django.apps import apps
from django.http import HttpRequest

from ts2.web.config import CommandAppConfig

from .apps import DiscordBotConfig
from .models import Server


class ServerCreateForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ['snowflake', 'invited_by', 'disabled']


class ServerPrefixForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ('prefix',)


class ServerExtensionsForm(forms.ModelForm):
    extensions = forms.CharField(required=False)

    class Meta:
        model = Server
        fields = ()

    def clean_extensions(self):
        data = self.cleaned_data['extensions']
        data = set(data.split(','))
        exts = {c.label for c in apps.get_app_configs()
                if isinstance(c, CommandAppConfig)}
        data = data & exts
        return ','.join(data)

    def save(self, commit: bool = True):
        self.instance._extensions = self.cleaned_data['extensions']
        return super().save(commit=commit)


class ServerModelSyncForm(forms.ModelForm):
    instance: Server

    class Meta:
        model = Server
        fields = ()

    @async_to_sync
    async def save(self, commit=True):
        app = DiscordBotConfig.get()
        thread = app.bot_thread

        async def task(bot):
            guild = await bot.fetch_guild(self.instance.snowflake)
            guild._channels = {c.id: c for c in await guild.fetch_channels()}
            guild._roles = {r.id: r for r in await guild.fetch_roles()}
            await bot.sync_server(guild)

        thread.run_coroutine(task(thread.client))
        return self.instance

    def user_tests(self, req: HttpRequest) -> bool:
        return req.user.is_superuser