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
from django.core.exceptions import ValidationError

from telescope2.discord.apps import DiscordBotConfig
from telescope2.discord.models import Server
from telescope2.utils.forms import AsyncFormMixin, D3SelectWidget, \
    FormConstants, SwitchInput, find_widgets, gen_labels


class PreferenceForms:
    def __init__(self, context):
        from .contexts import DiscordContext
        self.context: DiscordContext = context

    def prefix(self):
        return CommandPrefixForm(instance=self.context.server)

    def extensions(self):
        return ExtensionToggleForm(instance=self.context.server)

    def sync_models(self):
        return ModelSynchronizationActionForm(instance=self.context.server)

    def logging(self):
        return LoggingConfigFormset.get_form(self.context.server, self.context.is_superuser)


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


class CommandPrefixForm(FormConstants, AsyncFormMixin[Server], forms.ModelForm):
    async_writable = True

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
    async_writable = True

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
    async_writable = True

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

        thread.run_coroutine(task(thread.client))


channel_select_single = D3SelectWidget('discord:channels', 'single', prefix='#', classes='channel-list', placeholder='Select channel')
role_select_single = D3SelectWidget('discord:roles', 'single', prefix='@', classes='role-list', placeholder='Select role')


class LoggingConfigForm(FormConstants, forms.Form):
    key = forms.CharField(widget=forms.HiddenInput)
    name = forms.CharField(widget=forms.HiddenInput, required=False)
    channel = forms.IntegerField(required=False, label='Send logs to this channel', widget=channel_select_single)
    role = forms.IntegerField(required=False, label='Notify this role for every log message', widget=role_select_single)

    def clean(self):
        data = super().clean()
        channel = data.get('channel')
        role = data.get('role')
        if role and not channel:
            raise ValidationError('To set a role to notify, you must also specify a channel.')


class LoggingConfigFormset(forms.formset_factory(LoggingConfigForm, extra=0)):
    @classmethod
    def get_form(cls, server: Server, is_superuser: bool) -> LoggingConfigFormset:
        items = [
            {'key': 'MissingAnyRole', 'name': 'Constraint violations'},
            {'key': 'UserInputError', 'name': 'Bad command invocations'},
        ]
        if is_superuser:
            items.insert(0, {'key': 'Exception', 'name': 'Uncaught exceptions'})

        config = server.logging
        for row in items:
            key = row['key']
            err_type = config.get(key, {})
            if not err_type:
                continue
            try:
                row['channel'] = err_type.get('channel', '')
                row['role'] = err_type.get('role', '')
            except AttributeError:
                continue

        return cls(initial=items)

    def save(self, server: Server):
        conf = {}
        for row in self.cleaned_data:
            channel = row['channel']
            if not channel:
                continue
            conf[row['key']] = {
                'name': row['name'],
                'channel': channel,
                'role': row['role'],
            }
        server.logging = conf
        server.save()
