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

from telescope2.utils.templates import (domtokenlist, optional_attr,
                                        create_tag_parser, unwrap)

from ..utils.forms import AsyncModelForm

register = Library()


@create_tag_parser(register, 'asyncform', 'endform')
class AsyncFormNode(Node):
    def __init__(self, nodelist: NodeList, form: Variable, id: Variable = None, classes: Variable = None):
        self.nodelist = nodelist
        self.form = form
        self.id = id
        self.classes = classes

    def render(self, context: Context) -> str:
        form = self.form.resolve(context)
        if not isinstance(form, AsyncModelForm):
            raise TypeError(f'{repr(form)} must be a subclass of {AsyncModelForm}')
        endpoint = form.mutation_endpoint
        form_html = self.nodelist.render(context)
        section_id = optional_attr('id', unwrap(context, self.id))
        classes = optional_attr('class', domtokenlist('form async-form', unwrap(context, self.classes)))
        return mark_safe(f'<form {section_id} {classes} data-endpoint="{endpoint}">{form_html}</form>')


@register.simple_tag
def asyncsubmit(name: str, color: str, classes: str = ''):
    classes = domtokenlist(f'btn btn-{color} async-form-submit {classes}')
    return mark_safe(f'<button type="button" class="{classes}">{name}</button>')
