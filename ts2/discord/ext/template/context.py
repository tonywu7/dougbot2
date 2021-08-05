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

from collections.abc import Mapping
from datetime import datetime, timezone
from types import FunctionType

from discord.ext.commands import Context


class _Exposed:
    def __init__(self):
        self.attrs: set[str] = set()

    def __call__(self, f: FunctionType):
        self.attrs.add(f.__name__)
        return f

    def __iter__(self):
        return iter(self.attrs)


exposed = _Exposed()


class BaseContext:
    ctx: Context


class DateTimeContext(BaseContext):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._epoch = datetime.now(timezone.utc)

    @property
    @exposed
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    @property
    @exposed
    def epoch(self) -> datetime:
        return self._epoch


class CommandContext(DateTimeContext, Mapping):
    def __init__(self, ctx: Context, variables: dict[str], **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.namespace = {k: True for k in exposed}
        self.variables = variables

    def __getitem__(self, k: str):
        try:
            return self.variables[k]
        except KeyError:
            pass
        if k not in self.namespace:
            raise KeyError(k)
        return getattr(self, k)

    def __iter__(self):
        return iter({**self.namespace, **self.variables}.keys())

    def __len__(self) -> int:
        return len({**self.namespace, **self.variables})
