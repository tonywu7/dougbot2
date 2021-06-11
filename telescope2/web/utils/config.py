# base.py
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

from typing import Iterable, List

from django.apps import AppConfig
from django.urls.resolvers import URLPattern
from django.utils.module_loading import import_string
from django.utils.safestring import SafeString

from telescope2.web.utils.urls import AnnotatedPattern


class CommandAppConfig(AppConfig):
    label: str
    display_name: str
    icon: SafeString

    def public_views(cls) -> List[AnnotatedPattern]:
        routes: Iterable[URLPattern] = import_string(f'{cls.name}.urls.public_views')
        return [r.pattern for r in routes]
