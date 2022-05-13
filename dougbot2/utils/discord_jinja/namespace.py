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

from collections.abc import Mapping, Set
from types import FunctionType


class NamespaceRecord:
    def __init__(self):
        self.attrs: set[str] = set()

    def __call__(self, f: FunctionType):
        self.attrs.add(f.__name__)
        return f

    def __iter__(self):
        return iter(self.attrs)


class AttributeMapping(Mapping):
    _namespace: Set[str]

    def __init_subclass__(cls):
        super().__init_subclass__()
        exposed_attrs = []
        for attr in dir(cls):
            record = getattr(cls, attr, None)
            if isinstance(record, NamespaceRecord):
                exposed_attrs.append(record)
        if not hasattr(cls, "_namespace"):
            namespace = set()
        else:
            namespace = set(cls._namespace)
        namespace.update(*exposed_attrs)
        cls._namespace = frozenset(namespace)

    def __getitem__(self, k: str):
        if k not in self._namespace:
            raise KeyError(k)
        return getattr(self, k)

    def __iter__(self):
        return iter(self._namespace.keys())

    def __len__(self) -> int:
        return len(self._namespace.keys())
