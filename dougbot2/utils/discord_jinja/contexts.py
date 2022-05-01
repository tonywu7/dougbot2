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

from contextvars import ContextVar
from datetime import datetime, timezone

from discord.ext.commands import Context
from jinja2 import StrictUndefined

from .models import Member, Message
from .namespace import AttributeMapping, NamespaceRecord

ctx: ContextVar[Context] = ContextVar('ctx')


class BaseContext:
    ctx: Context


class DateTimeContext(BaseContext):
    _ns_datetime = NamespaceRecord()

    def __init__(self):
        super().__init__()
        self._epoch = datetime.now(timezone.utc)

    @property
    @_ns_datetime
    def now(self) -> datetime:
        return datetime.now(timezone.utc)

    @property
    @_ns_datetime
    def epoch(self) -> datetime:
        return self._epoch


class MessageContext(BaseContext):
    _ns_message = NamespaceRecord()

    @property
    @_ns_message
    def author(self) -> Member:
        return Member(self.ctx.author)

    @property
    @_ns_message
    def message(self) -> Message:
        return Message(self.ctx.message)


class TemplateContext(
    AttributeMapping,
    DateTimeContext,
    MessageContext,
):
    def __init__(self):
        super().__init__()

    @property
    def ctx(self) -> Context:
        current_ctx = ctx.get(None)
        if current_ctx is None:
            return StrictUndefined('No running command')
        return current_ctx


def set_context(context: Context):
    ctx.set(context)


def get_context() -> Context:
    return ctx.get()
