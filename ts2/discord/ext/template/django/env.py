# MIT License
#
# Copyright (c) 2021 @tonyzbf +https://github.com/tonyzbf/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
from ..env import CommandEnvironment

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


class DjangoEnvironment(CommandEnvironment):
    @sync_to_async
    def get_template_async(self, name: str | Template, parent=None, globals=None) -> Template:
        return self.get_template(name, parent, globals)


def get_environment():
    return DjangoEnvironment(
        loader=ModelLoader(),
        bytecode_cache=MemcachedBytecodeCache(caches['jinja2']),
        autoescape=select_autoescape(),
        enable_async=True,
    )
