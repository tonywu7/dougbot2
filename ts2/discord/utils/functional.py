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

from functools import partial
from typing import TypeVar

_MISS = object()

T = TypeVar('T')
U = TypeVar('U')


def memoize(obj: object, k: str, *args, factory=list, setter=list.append):
    """Memoize metadata about a function so that decorators can be applied in arbitrary orders."""
    memo: list
    try:
        memo = getattr(obj, k)
    except AttributeError:
        memo = factory()
        setattr(obj, k, memo)
    setter(memo, *args)
    return obj


dict_memoize = partial(memoize, factory=dict, setter=dict.__setitem__)


def get_memo(obj, k: str, *members: str, default: T) -> T:
    """Get a previously memoized attribute from an object."""
    memo = getattr(obj, k, _MISS)
    if memo is not _MISS:
        return memo
    for attr in members:
        try:
            member = getattr(obj, attr)
        except AttributeError:
            continue
        memo = getattr(member, k, _MISS)
        if memo is not _MISS:
            return memo
    return default
