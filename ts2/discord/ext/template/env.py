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

from discord.ext.commands import Context
from jinja2 import Environment, select_autoescape

from .context import CommandContext
from .filters import register_filters

default_env = None


class CommandEnvironment(Environment):
    async def render(self, ctx: Context, source: str, variables: dict):
        cctx = CommandContext(ctx, variables)
        tmpl = self.from_string(source)
        return await tmpl.render_async(**cctx)

    async def render_timed(self, ctx: Context, source: str,
                           variables: dict, timeout: float = 10):
        renderer = self.render(ctx, source, variables)
        result = await asyncio.wait_for(renderer, timeout=timeout)
        return result


T_E = TypeVar('T_E', bound=CommandEnvironment)


def make_environment(class_: Type[T_E] = CommandEnvironment, **options) -> T_E:
    options.setdefault('loader', None)
    options.setdefault('bytecode_cache', None)
    options.setdefault('autoescape', select_autoescape())
    options['enable_async'] = True
    env = class_(**options)
    register_filters(env)
    return env


def get_environment() -> CommandEnvironment:
    global default_env
    if not default_env:
        default_env = make_environment()
    return default_env
