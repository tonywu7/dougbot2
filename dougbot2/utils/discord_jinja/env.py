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

import asyncio
from typing import Any, Mapping, Optional, Type, TypeVar, Union

from jinja2 import StrictUndefined, Template, select_autoescape
from jinja2.runtime import Context
from jinja2.sandbox import SandboxedEnvironment
from jinja2.utils import missing

from .contexts import TemplateContext, set_context
from .filters import register_filters

default_env = None


class CommandContext(Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cmd_ctx = TemplateContext()

    def resolve_or_missing(self, key: str):
        res = super().resolve_or_missing(key)
        if res is not missing:
            return res
        try:
            return self._cmd_ctx[key]
        except KeyError:
            return missing


class CommandTemplate(Template):
    @property
    def source(self) -> Optional[str]:
        try:
            return self._source
        except AttributeError:
            return None

    @source.setter
    def source(self, src: str):
        self._source = src

    async def render(self, ctx: Optional[Context], **variables) -> str:
        set_context(ctx)
        return await super().render_async(**variables)

    async def render_timed(self, ctx: Optional[Context], timeout: float = 10.0,
                           **variables) -> str:
        renderer = self.render(ctx, **variables)
        result = await asyncio.wait_for(renderer, timeout=timeout)
        return result

    render_async = render


class CommandEnvironment(SandboxedEnvironment):
    def from_string(
        self, source: Union[str, CommandTemplate],
        globals: Optional[Mapping[str, Any]] = None,
        template_class: Optional[type[CommandTemplate]] = CommandTemplate,
    ) -> CommandTemplate:
        tmpl: CommandTemplate
        tmpl = super().from_string(source, globals, template_class)
        tmpl.source = source
        return tmpl


T_E = TypeVar('T_E', bound=CommandEnvironment)
T_C = TypeVar('T_C', bound=CommandContext)


def make_environment(
    env_cls: Type[T_E] = CommandEnvironment,
    ctx_cls: Type[T_C] = CommandContext,
    **options,
) -> T_E:
    options.setdefault('loader', None)
    options.setdefault('bytecode_cache', None)
    options.setdefault('autoescape', select_autoescape())
    options.setdefault('undefined', StrictUndefined)
    options.setdefault('extensions', ['jinja2.ext.do'])
    options['enable_async'] = True
    env = env_cls(**options)
    env.context_class = ctx_cls
    register_filters(env)
    return env


def get_environment() -> CommandEnvironment:
    global default_env
    if not default_env:
        default_env = make_environment()
    return default_env
