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

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from django.template import Context, Library, Node, NodeList, Variable, loader
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

from ts2.web.utils.templates import (create_tag_parser, domtokenlist,
                                     optional_attr, unwrap)

register = Library()


@create_tag_parser(register, 'set', 'endset')
class BlockAssignmentNode(Node):
    def __init__(self, nodelist: NodeList, var_name: Variable) -> None:
        self.nodelist = nodelist
        self.var_name = var_name.var

    def render(self, context: Context) -> str:
        context[self.var_name] = self.nodelist.render(context)
        return ''


@create_tag_parser(register, 'section', 'endsection')
@dataclass
class SectionNode(Node):
    nodelist: NodeList
    id: str
    title: str
    classes: str = ''

    def render(self, context: Context) -> str:
        content = self.nodelist.render(context)
        title = unwrap(context, self.title)
        section_id = optional_attr('id', unwrap(context, self.id))
        classes = optional_attr('class', domtokenlist('main-section', unwrap(context, self.classes)))
        return mark_safe(
            f'<section {section_id} {classes}>'
            f'<header><h3>{mark_safe(title)}</h3></header>'
            f'<div class="interactive-text section-content">{content}</div></section>',
        )


@create_tag_parser(register, 'sidebarlink')
@dataclass
class SidebarLinkNode(Node):
    view: Variable
    name: Variable
    icon: Variable

    def render(self, context: Context) -> str:
        mark_active: Optional[Callable] = context.get('mark_active')
        view = unwrap(context, self.view)
        icon = unwrap(context, self.icon)
        name = unwrap(context, self.name)
        try:
            snowflake = context['discord'].server_id
            url = reverse(view, kwargs={'guild_id': snowflake})
        except (KeyError, NoReverseMatch):
            url = reverse(view)
        if 'request' in context and view == context['request'].resolver_match.view_name:
            classes = ' class="sidebar-active"'
            if mark_active:
                mark_active(url)
        else:
            classes = ''
        return mark_safe(f'<li><span{classes}>{icon}</i><a href="{url}">{name}</a></span></li>')


@create_tag_parser(register, 'chapter', 'endchapter')
@dataclass
class SidebarSectionNode(Node):
    nodelist: NodeList
    id: str
    name: str
    icon: str
    parent_id: str = 'sidebar'

    def render(self, context: Context) -> str:
        active_route = None

        def mark_active_cb(url):
            nonlocal active_route
            active_route = url

        with context.push():
            context['mark_active'] = mark_active_cb
            content = self.nodelist.render(context)

        parent_id = unwrap(context, self.parent_id)
        chapter_id = unwrap(context, self.id)
        body_id = f'{chapter_id}-routes'
        name = unwrap(context, self.name)
        icon = unwrap(context, self.icon)

        if active_route:
            header_cls = 'accordion-button'
            body_cls = 'collapse show'
            expanded = 'true'
        else:
            header_cls = 'accordion-button collapsed'
            body_cls = 'collapse'
            expanded = 'false'

        return mark_safe(
            '<div class="accordion-item">'
            f'    <h2 id="{chapter_id}" class="accordion-header {header_cls}" data-bs-toggle="collapse"'
            f'         data-bs-target="#{body_id}" role="button" aria-expanded="{expanded}">'
            f'        {icon}<span tabindex="0">{name}</span></h2>'
            f'    <div id="{body_id}" class="accordion-collapse {body_cls}" data-bs-parent="#{parent_id}">'
            f'        <div class="accordion-body"><ul>{content}</ul>'
            '</div></div></div>',
        )


@register.simple_tag(name='bs5switch')
def bootstrap5switch(field):
    template = loader.get_template('telescope2/elements/switch.html')
    return template.render({'field': field})
