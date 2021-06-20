# inspect.py
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
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=False)
def pkg_version():
    """Return package version string."""
    from ...settings import __version__
    return __version__


@register.simple_tag(takes_context=False)
def pkg_version_string():
    """Return package and module version string."""
    from aiohttp import __version__ as aiohttp_version
    from discord import __version__ as discord_version
    from django import __version__ as django_version

    from ...settings import __version__
    return mark_safe(f'<code>{settings.APP_NAME}/{__version__}</code> '
                     f'<code>aiohttp/{aiohttp_version}</code> '
                     f'<code>discord.py/{discord_version}</code> '
                     f'<code>django/{django_version}</code>')


@register.simple_tag(takes_context=True)
def basefilename(context):
    """Return filename minus the extension."""
    return context.template_name.split('.')[0]


@register.simple_tag(takes_context=True)
def fullfilename(context):
    """Return full filename with the extension."""
    return context.template_name


@register.simple_tag(takes_context=True)
def viewname(context: template.Context):
    try:
        req = context['request']
        return req.resolver_match.view_name
    except Exception:
        return ''
