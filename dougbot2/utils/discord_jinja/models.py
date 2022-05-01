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

from typing import Optional

import discord as d
from markupsafe import Markup


class Color:
    def __init__(self, color: d.Colour):
        self._color = color

    def __index__(self) -> int:
        return self._color.value

    __int__ = __index__

    def __str__(self):
        return hex(self._color.value)


class Member:
    def __init__(self, member: d.Member):
        self._member = member

    def __str__(self):
        return str(self._member)

    @property
    def id(self) -> int:
        return self._member.id

    @property
    def discriminator(self) -> str:
        return self._member.discriminator

    @property
    def name(self) -> str:
        return self._member.display_name

    @property
    def username(self) -> Optional[str]:
        return self._member.name

    @property
    def nickname(self) -> str:
        return self._member.nick

    @property
    def tag(self) -> str:
        return Markup(self._member.mention)

    @property
    def color(self) -> Color:
        return Color(self._member.color)


class Message:
    def __init__(self, message: d.Message) -> None:
        self._message = message

    @property
    def id(self) -> int:
        return self._message.id

    @property
    def author(self) -> Member:
        return Member(self._message.author)

    @property
    def content(self) -> str:
        return Markup(self._message.content)
