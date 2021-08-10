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

import pytest
from duckcord.color import Color2


def test_init():
    Color2(0)


def test_casting():
    c = Color2(127)
    assert 127 == int(c)
    assert '0x7f' == hex(c)


def test_equality():
    assert Color2(255) == Color2(255)
    assert Color2(255) != Color2(256)


def test_idempotent_init():
    assert Color2(Color2(37)).value == 37


def test_hashing():
    c = Color2(255)
    d1 = {255: True}
    d2 = {c: True}
    assert c not in d1
    assert 255 not in d2


def test_immutability():
    with pytest.raises(NotImplementedError):
        Color2(511).value = 512
