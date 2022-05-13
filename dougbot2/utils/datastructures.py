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

from collections.abc import MutableMapping
from typing import Optional, TypeVar, Union, get_args, get_origin

MAX_SAFE_INTEGER = 2**53

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class BigIntDict(MutableMapping[_KT, _VT]):
    """A mutable mapping in which string representations of a JavaScript big integer\
    (> 2^53) are converted to int before being used as keys."""

    def __init__(self, mapping: Optional[MutableMapping[_KT, _VT]]) -> None:
        if mapping:
            self._map = {self._convert(k): v for k, v in mapping.items()}
        else:
            self._map = {}

    def _convert(self, k: Union[str, int]):
        if isinstance(k, int):
            return k
        try:
            num_k = int(k)
        except ValueError:
            return k
        if num_k < MAX_SAFE_INTEGER:
            return k
        return num_k

    def __getitem__(self, k):
        return self._map[self._convert(k)]

    def __setitem__(self, k, v):
        self._map[self._convert(k)] = v

    def __delitem__(self, k):
        del self._map[self._convert(k)]

    def __iter__(self):
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._map)


class TypeDictionary(MutableMapping[_KT, _VT]):
    """Mutable mapping type with support for inheritance-enabled item lookup.

    Behaves like a regular dict when getting an item using non-type objects.
    When looking up a type, tries to look up the type's super classes in
    its method resolution order and returns the first result.
    """

    def __init__(self, mapping: Optional[dict[_KT, _VT]] = None):
        self._dict = {**mapping} if mapping else {}

    def contains_exact(self, k: _KT) -> bool:
        return k in self._dict

    def __getitem__(self, k: _KT) -> _VT:
        if get_origin(k) is Union:
            k = frozenset(get_args(k))
        mapping = self._dict
        try:
            return mapping[k]
        except KeyError:
            pass
        if not isinstance(k, type):
            raise KeyError(k)
        for cls in k.mro():
            try:
                return mapping[cls]
            except KeyError:
                pass
        raise KeyError(k)

    def __setitem__(self, k: _KT, v: _VT):
        if get_origin(k) is Union:
            # Use the set of a union type's constituent types
            # as the key for the union type
            self._dict[frozenset(get_args(k))] = v
        elif isinstance(k, tuple):
            for item in k:
                self._dict[item] = v
        else:
            self._dict[k] = v

    def __delitem__(self, k: _KT):
        del self._dict[k]

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)
