# config.py
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

from collections.abc import Callable, Iterable
from functools import partial
from typing import Optional

from discord.ext.commands import Cog
from django.apps import AppConfig
from django.urls.resolvers import RegexPattern, RoutePattern, URLPattern
from django.utils.functional import classproperty
from django.utils.module_loading import import_string
from django.utils.safestring import SafeString, mark_safe


class CommandAppConfig(AppConfig):
    """Subclass of Django AppConfig with extra metadata for displaying on webpages."""

    @classproperty
    def title(cls) -> str:
        """Return the title of this app."""
        raise NotImplementedError

    @classproperty
    def icon(cls) -> SafeString:
        """Return the HTML markup for the icon of this app."""
        raise NotImplementedError

    @classproperty
    def target(cls) -> Cog:
        """Return the discord.py cog associated with this Django app."""
        raise NotImplementedError

    @classproperty
    def icon_and_title(cls) -> SafeString:
        """Return the icon and title as HTML markup."""
        return mark_safe(f'{cls.icon} {cls.title}')

    @classproperty
    def hidden(self) -> bool:
        """Return True if this app should be hidden from the web console."""
        return False

    label: str
    default = False

    def public_views(cls) -> list[AnnotatedPattern]:
        """Return the list of endpoints from this app that should appear in the web console sidebar."""
        try:
            routes: Iterable[URLPattern] = import_string(f'{cls.name}.urls.public_views')
            return [r.pattern for r in routes]
        except ModuleNotFoundError:
            return []


class AnnotatedPattern:
    """Mixin for Django URL pattern classes containing cosmetic metadata such as titles and icons."""

    name: str

    def __init__(self, *args, title: str, icon: str, color: Optional[int] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.color = color
        self.icon = icon


class AnnotatedRoutePattern(AnnotatedPattern, RoutePattern):
    """Django RoutePattern containing metadata on how it should be displayed in a webpage."""

    pass


class AnnotatedRegexPattern(AnnotatedPattern, RegexPattern):
    """Django RegexPattern containing metadata on how it should be displayed in a webpage."""

    pass


def annotated(route: str, view: Callable, name: str, title: str, icon: str,
              color: Optional[int] = None, kwargs=None, pattern_t=AnnotatedRegexPattern):
    """Create a Django `URLPattern` with additional info.

    :param route: The URL route.
    :type route: str
    :param view: The associated view function.
    :type view: Callable
    :param name: The name of the route used for reverse lookup.
    :type name: str
    :param title: The title of the endpoint to be displayed on a webpage.
    :type title: str
    :param icon: The icon of the endpoint to be displayed on a webpage.
    :type icon: str
    :param color: The text color of the displayed hyperlink, defaults to None
    :type color: Optional[int], optional
    :param pattern_t: The `URLPattern` subclass to use, defaults to `AnnotatedRegexPattern`
    :type pattern_t: URLPattern, optional
    :return: The created URL pattern object.
    :rtype: URLPattern
    """
    pattern = pattern_t(route, name=name, is_endpoint=True,
                        title=title, icon=icon, color=color)
    return URLPattern(pattern, view, kwargs, name)


annotated_path = partial(annotated, pattern_t=AnnotatedRoutePattern)
annotated_re_path = partial(annotated, pattern_t=AnnotatedRegexPattern)
