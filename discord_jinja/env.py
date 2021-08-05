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
from typing import Type, TypeVar

from jinja2 import Environment, StrictUndefined, select_autoescape
from jinja2.runtime import Context
from jinja2.utils import missing

from .contexts import TemplateContext, set_command_context
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


class CommandEnvironment(Environment):
    async def render(self, ctx: Context, source: str, variables: dict):
        set_command_context(ctx)
        tmpl = self.from_string(source)
        return await tmpl.render_async(**variables)

    async def render_timed(self, ctx: Context, source: str,
                           variables: dict, timeout: float = 10):
        renderer = self.render(ctx, source, variables)
        result = await asyncio.wait_for(renderer, timeout=timeout)
        return result

    def getattr(self, obj, attribute: str):
        # Forbid access to "private" members including magic methods.
        # Otherwise any template will have access to builtins through
        # function.__globals__
        if attribute[0] == '_':
            return self.undefined('Private member access forbidden.',
                                  obj=obj, name=attribute)
        return super().getattr(obj, attribute)


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
