# async_form.py
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

from django.template import Context, Library, Node, NodeList, Variable
from django.utils.safestring import mark_safe

from ..utils.templates import (create_tag_parser, domtokenlist, optional_attr,
                               unwrap)

register = Library()


@create_tag_parser(register, 'bsform', 'endform')
class BootstrapFormNode(Node):
    def __init__(self, nodelist: NodeList, id: Variable = None, classes: Variable = None):
        self.nodelist = nodelist
        self.id = id
        self.classes = classes

    def get_server_id(self, context: Context) -> str:
        return context['discord'].server_id

    def render(self, context: Context) -> str:
        form_html = self.nodelist.render(context)
        section_id = optional_attr('id', unwrap(context, self.id))
        classes = optional_attr('class', domtokenlist('form', unwrap(context, self.classes)))
        return mark_safe(f'<form {section_id} {classes}>{form_html}</form>')


@register.simple_tag
def bsfields(form):
    return mark_safe(f'<ul class="form-fields">{form.as_ul()}</ul>')


@register.simple_tag
def bsbutton(name: str, color: str, classes: str = '', action: str = ''):
    classes = domtokenlist('btn', f'btn-{color}', classes)
    action = optional_attr('v-on:click', action)
    return mark_safe(f'<button type="button" {action} class="{classes}">{name}</button>')
