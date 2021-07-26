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

from ..models import Feature
from ..utils.templates import (create_tag_parser, domtokenlist, optional_attr,
                               unwrap)

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
            f'<header><h3 class="section-header">{mark_safe(title)}</h3></header>'
            f'<div class="section-content">{content}</div></section>',
        )


def reverse_universal(ctx: Context, view: str, **kwargs):
    try:
        snowflake = ctx['discord'].server_id
        url = reverse(view, kwargs={'guild_id': snowflake, **kwargs})
    except (AttributeError, KeyError, NoReverseMatch):
        url = None
    if not url:
        url = reverse(view, kwargs=kwargs)
    return url


@create_tag_parser(register, 'sidebarlink')
class SidebarLinkNode(Node):
    def __init__(self, view: Variable, name: Variable, icon: Variable, **url_kwargs):
        self.view = view
        self.name = name
        self.icon = icon
        self.kwargs = url_kwargs

    def render(self, context: Context) -> str:
        mark_active: Optional[Callable] = context.get('mark_active')
        view = unwrap(context, self.view)
        icon = unwrap(context, self.icon)
        name = unwrap(context, self.name)
        url_kwargs = unwrap(context, self.kwargs)
        try:
            url = reverse_universal(context, view, **url_kwargs)
        except NoReverseMatch:
            return mark_safe('')
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

        if not content or content.isspace():
            return mark_safe('')

        ctx = {'content': content}
        ctx['parent_id'] = unwrap(context, self.parent_id)
        ctx['chapter_id'] = chapter_id = unwrap(context, self.id)
        ctx['body_id'] = f'{chapter_id}-routes'
        ctx['name'] = unwrap(context, self.name)
        ctx['icon'] = mark_safe(unwrap(context, self.icon))

        if active_route:
            ctx['header_cls'] = 'accordion-button'
            ctx['body_cls'] = 'collapse show'
            ctx['expanded'] = 'true'
        else:
            ctx['header_cls'] = 'accordion-button collapsed'
            ctx['body_cls'] = 'collapse'
            ctx['expanded'] = 'false'

        tmpl = loader.get_template('ts2/web/elements/sidebar-section.html')
        return tmpl.render(ctx)


@register.simple_tag(name='bs5switch')
def bootstrap5switch(field):
    template = loader.get_template('telescope2/elements/switch.html')
    return template.render({'field': field})


@register.simple_tag(name='featurelink', takes_context=True)
def featurenode(context: Context, slug: str):
    try:
        feature: Feature = Feature.objects.filter(slug=slug).get()
    except Feature.DoesNotExist:
        return mark_safe(
            '<span class="text-danger">'
            f'Feature #{slug} (not found)</span>',
        )
    url = reverse_universal(context, 'web:features')
    return mark_safe(
        f'<a href="{url}#{feature.slug}" '
        f'    class="feature-link feature-type type-{feature.ftype}">'
        f'Feature {feature.id} #{feature.slug}'
        '</a>',
    )


@register.simple_tag(name='url-universal', takes_context=True)
def universal_url(context: Context, endpoint: str, **kwargs):
    return reverse_universal(context, endpoint, **kwargs)
