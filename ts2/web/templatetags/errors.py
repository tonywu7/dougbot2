# errors.py
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
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def httpstatus(context):
    """Return rendered HTTP status code based on the error template name."""
    ERRORS = {
        '400': ('Bad Request', 'warning'),
        '401': ('Unauthorized', 'warning'),
        '403': ('Forbidden', 'danger'),
        '404': ('Not Found', 'info'),
        '405': ('Method Not Allowed', 'warning'),
        '451': ('Unavailable For Legal Reasons', 'warning'),
        '500': ('Internal Server Error', 'warning'),
        '503': ('Service Unavailable', 'danger'),
    }
    err = context.template_name.split('.')[0]
    msg, level = ERRORS.get(err, (None, None))
    if not msg:
        return ''
    return mark_safe(
        f'<span class="text-{level} http-status">HTTP <a href="'
        f'https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/{err}">'
        f'<code>{err}</code></a> {msg}</span>',
    )
