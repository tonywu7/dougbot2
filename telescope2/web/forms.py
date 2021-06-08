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

from operator import itemgetter

from django import forms

from telescope2.discord.models import Server


class UserCreateForm(forms.Form):
    username = forms.CharField()
    discord_id = forms.IntegerField()

    access_token = forms.CharField()
    refresh_token = forms.CharField()
    expires_at = forms.IntegerField()

    @property
    def itemgetter(self) -> itemgetter:
        return itemgetter(*self.fields.keys())

    def to_tuple(self):
        return self.itemgetter(self.cleaned_data)


class ServerCreateForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = ['gid']
