# pathfinding.py
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

from django import template
from django.conf import settings
from django.templatetags.static import static as static_path

register = template.Library()


@register.simple_tag
def staticserver():
    if settings.DEBUG or settings.STATIC_SERVER is None:
        return ''
    return settings.STATIC_SERVER


@register.simple_tag
def static(path: str):
    path = static_path(path)
    if settings.DEBUG or settings.STATIC_SERVER is None:
        return path
    return f'{settings.STATIC_SERVER}{path}'
