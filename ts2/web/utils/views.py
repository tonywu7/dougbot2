# views.py
# Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse

RequestHandler = Callable[[HttpRequest], HttpResponse]
InstanceRequestHandler = Callable[[Any, HttpRequest], HttpResponse]


def with_self(*decorators: RequestHandler) -> Callable[[InstanceRequestHandler], InstanceRequestHandler]:
    def wrapper(f: InstanceRequestHandler):
        def preprocess(req: HttpRequest, *args, **kwargs):
            return req, args, kwargs
        for d in decorators:
            preprocess = d(preprocess)

        @wraps(f)
        def wrapped(self, req: HttpRequest, *args, **kwargs) -> HttpResponse:
            req, args, kwargs = preprocess(req, *args, **kwargs)
            return f(self, req, *args, **kwargs)
        return wrapped
    return wrapper
