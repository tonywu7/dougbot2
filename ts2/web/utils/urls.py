# urls.py
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

# TODO: remove

from collections.abc import Callable
from functools import partial
from typing import Optional

from django.urls.resolvers import RegexPattern, RoutePattern, URLPattern


class AnnotatedPattern:
    name: str

    def __init__(self, *args, title: str, icon: str, color: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.color = color
        self.icon = icon


class AnnotatedRoutePattern(AnnotatedPattern, RoutePattern):
    pass


class AnnotatedRegexPattern(AnnotatedPattern, RegexPattern):
    pass


def annotated(route: str, view: Callable, name: str, title: str, icon: str,
              color: Optional[int] = None, kwargs=None, pattern_t=AnnotatedRegexPattern):
    pattern = pattern_t(route, name=name, is_endpoint=True,
                        title=title, icon=icon, color=color)
    return URLPattern(pattern, view, kwargs, name)


annotated_path = partial(annotated, pattern_t=AnnotatedRoutePattern)
annotated_re_path = partial(annotated, pattern_t=AnnotatedRegexPattern)
