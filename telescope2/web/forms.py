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

import re
from operator import itemgetter

from django import forms

from telescope2.discord.models import Server

from .utils.forms import (AsyncModelForm, FormConstants, find_widgets,
                          gen_labels)


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


class CommandPrefixForm(FormConstants, AsyncModelForm):
    FORBIDDEN_PREFIXES = re.compile(r'^[*_|~`>]+$')

    class Meta:
        model = Server
        fields = ['prefix']
        labels = gen_labels(Server)
        widgets = {**find_widgets(Server)}

    def clean_prefix(self):
        data = self.cleaned_data['prefix']
        if self.FORBIDDEN_PREFIXES.match(data):
            raise forms.ValidationError(
                '* _ | ~ ` > are markdown characters. '
                '%(prefix)s as a prefix will cause messages with markdowns '
                'to trigger bot commands.',
                params={'prefix': data},
                code='forbidden_chars',
            )
        return data


class PreferenceForms:
    def __init__(self, context):
        from .contexts import DiscordContext
        self.context: DiscordContext = context

    def prefix(self):
        return CommandPrefixForm(instance=self.context.prefs)