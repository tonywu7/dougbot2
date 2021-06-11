# element.py
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

from django.template import Context, Library, Node, NodeList, Variable
from django.urls import reverse
from django.utils.safestring import mark_safe

from telescope2.utils.templates import optional_attr, register_autotag, unwrap

register = Library()



@register_autotag(register, 'set', 'endset')
class BlockAssignmentNode(Node):
    def __init__(self, nodelist: NodeList, var_name: Variable) -> None:
        self.nodelist = nodelist
        self.var_name = var_name.var

    def render(self, context: Context) -> str:
        context[self.var_name] = self.nodelist.render(context)
        return ''


@register_autotag(register, 'section', 'endsection')
class SectionNode(Node):
    def __init__(self, nodelist: NodeList, id: Variable,
                 title: Variable, classes: Variable = ''):

        self.nodelist = nodelist
        self.id = id
        self.title = title
        self.classes = classes

    def render(self, context: Context) -> str:
        content = self.nodelist.render(context)
        title = unwrap(context, self.title)
        section_id = optional_attr('id', unwrap(context, self.id))
        classes = optional_attr('class', unwrap(context, self.classes))
        return mark_safe(
            f'<section {section_id} {classes}>'
            f'<header><h3>{mark_safe(title)}</h3></header>'
            f'<div class="interactive-text section-content">{content}</div></section>',
        )


@register.simple_tag(takes_context=True)
def sidebarlink(context, icon, view, name):
    gid = context['discord'].current.id
    url = reverse(view, kwargs={'guild_id': gid})
    if view == context['request'].resolver_match.view_name:
        classes = ' class="sidebar-active"'
    else:
        classes = ''
    return mark_safe(f'<span{classes}><i class="bi bi-{icon}"></i><a href="{url}">{name}</a></span>')
