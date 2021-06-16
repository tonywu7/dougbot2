# discord_list.py
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

from dataclasses import dataclass
from typing import Optional

from django.template import Context, Library, Node, NodeList, Template
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from telescope2.utils.templates import create_tag_parser, domtokenlist, \
    optional_attr, unwrap

register = Library()


@create_tag_parser(register, 'd3itemlist', 'enditemlist')
@dataclass
class D3ItemList(Node):
    nodelist: NodeList
    endpoint: str
    type: str
    id: str = ''
    name: str = ''
    initial: Optional[str] = None
    placeholder: str = '...'
    classes: str = ''

    def render(self, ctx: Context):
        prefix = mark_safe(self.nodelist.render(ctx))
        tmpl: Template = get_template('telescope2/web/elements/item-list.html')
        select_type = unwrap(ctx, self.type)
        autoclose = 'true' if select_type == 'single' else 'outside'
        return tmpl.render({
            'endpoint': unwrap(ctx, self.endpoint),
            'type': select_type,
            'prefix': prefix,
            'id': optional_attr('id', unwrap(ctx, self.id)),
            'name': optional_attr('name', unwrap(ctx, self.id)),
            'value': optional_attr('value', unwrap(ctx, self.initial)),
            'placeholder': unwrap(ctx, self.placeholder),
            'autoclose': autoclose,
            'classes': optional_attr('class', domtokenlist('d3-item-list', unwrap(ctx, self.classes))),
        })
