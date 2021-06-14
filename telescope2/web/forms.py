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

from asgiref.sync import async_to_sync
from django import forms

from telescope2.discord.apps import DiscordBotConfig
from telescope2.discord.models import Server

from .utils.forms import (AsyncFormMixin, FormConstants, SwitchInput,
                          find_widgets, gen_labels)


class PreferenceForms:
    def __init__(self, context):
        from .contexts import DiscordContext
        self.context: DiscordContext = context

    def prefix(self):
        return CommandPrefixForm(instance=self.context.prefs)

    def extensions(self):
        return ExtensionToggleForm(instance=self.context.prefs)

    def sync_models(self):
        return ModelSynchronizationActionForm(instance=self.context.prefs)


class UserCreationForm(forms.Form):
    username = forms.CharField()
    snowflake = forms.IntegerField()

    access_token = forms.CharField()
    refresh_token = forms.CharField()
    expires_at = forms.IntegerField()

    @property
    def itemgetter(self) -> itemgetter:
        return itemgetter(*self.fields.keys())

    def to_tuple(self):
        return self.itemgetter(self.cleaned_data)


class ServerCreationForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ['snowflake']


class CommandPrefixForm(FormConstants, AsyncFormMixin, forms.ModelForm):
    class Meta:
        model = Server
        fields = ['prefix']
        labels = gen_labels(Server)
        widgets = {**find_widgets(Server)}

    def clean_prefix(self):
        data = self.cleaned_data['prefix']
        try:
            Server.validate_prefix(data)
        except ValueError as e:
            raise forms.ValidationError(str(e), code='forbidden_chars')
        return data


class ExtensionToggleForm(FormConstants, AsyncFormMixin[Server], forms.ModelForm):
    class Meta:
        model = Server
        fields = []

    def __init__(self, instance: Server, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.instance = instance
        conf = DiscordBotConfig.get()
        options = {}
        enabled = instance.extensions
        for label, ext in conf.extensions.items():
            options[label] = forms.BooleanField(
                required=False, label=ext.icon_and_title,
                initial=label in enabled, widget=SwitchInput,
            )
        self.fields.update(options)

    def save(self, commit=True):
        enabled = [k for k, v in self.cleaned_data.items() if v]
        self.instance.extensions = enabled
        super().save(commit=commit)


class ModelSynchronizationActionForm(FormConstants, AsyncFormMixin[Server], forms.ModelForm):
    class Meta:
        model = Server
        fields = ['snowflake']

    snowflake = forms.IntegerField(required=True, widget=forms.HiddenInput)

    @async_to_sync
    async def save(self, commit=True):
        app = DiscordBotConfig.get()
        thread = app.bot_thread

        async def task(bot):
            guild = await bot.fetch_guild(self.cleaned_data['snowflake'])
            guild._channels = {c.id: c for c in await guild.fetch_channels()}
            guild._roles = {r.id: r for r in await guild.fetch_roles()}
            await bot.sync_server(guild)

        with thread.data_requested:
            thread.set_request(task(thread.client))
            thread.data_requested.notify_all()
        with thread.data_ready:
            thread.data_ready.wait_for(thread.has_result)
            result = thread.get_result()
            if isinstance(result, Exception):
                raise result
