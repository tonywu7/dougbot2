# contrib.py
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

from django.template import Context, Library, Node, NodeList

from telescope2.utils.templates import create_tag_parser
from telescope2.www.templatetags.element import (SidebarLinkNode,
                                                 SidebarSectionNode)

from ..apps import DiscordBotConfig

register = Library()


@create_tag_parser(register, 'extensions_list')
class ExtensionListNode(Node):
    def __init__(self):
        super().__init__()

    def render(self, context: Context) -> str:
        url_map = DiscordBotConfig.url_map
        ext_map = DiscordBotConfig.ext_map
        text = []
        for (ext_name, urls), (_, conf) in zip(url_map.items(), ext_map.items()):
            nodelist = NodeList()
            for url in urls:
                view = f'web:ext:{ext_name}:{url.name}'
                nodelist.append(SidebarLinkNode(view, url.title, url.icon))
            chapter = SidebarSectionNode(nodelist, conf.label, conf.title, conf.icon)
            text.append(chapter.render(context))
        return '\n'.join(text)
