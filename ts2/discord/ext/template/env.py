# template.py
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
from pathlib import Path
from typing import Optional, TypeVar

from asgiref.sync import sync_to_async
from django.apps import apps
from django.core.cache import caches
from django.core.exceptions import ObjectDoesNotExist
from jinja2 import (BaseLoader, Environment, MemcachedBytecodeCache, Template,
                    TemplateNotFound, select_autoescape)

from .models import BaseTemplate

T = TypeVar('T', bound=BaseTemplate)


class ModelLoader(BaseLoader):
    def get_instance(self, template: str) -> T:
        path = Path(template)
        app_label = path.parts[0]
        model_name = path.parts[1]
        model: type[T] = apps.get_model(app_label, model_name)
        return model.objects.get(id=path.with_suffix('').name)

    def get_source(self, environment: Environment, template: str) -> tuple[str, Optional[str], Optional[Callable[[], bool]]]:
        try:
            tmpl = self.get_instance(template)
        except (ObjectDoesNotExist, LookupError) as e:
            raise TemplateNotFound(template, str(e))
        return tmpl.source, template, lambda: True


class AsyncEnvironment(Environment):
    @sync_to_async
    def get_template_async(self, name: str | Template, parent=None, globals=None) -> Template:
        return self.get_template(name, parent, globals)


env = AsyncEnvironment(
    loader=ModelLoader(),
    bytecode_cache=MemcachedBytecodeCache(caches['jinja2']),
    autoescape=select_autoescape(),
    enable_async=True,
)

__all__ = ['env']
