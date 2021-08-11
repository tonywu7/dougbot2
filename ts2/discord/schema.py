# schema.py
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

from typing import TypeVar, Union

from django.db.models import Model, QuerySet
from django.http import HttpRequest

from .middleware import get_ctx

M = TypeVar('M', bound=Model)


def get_server_model(
    q: Union[type[M], QuerySet[M]], req: HttpRequest,
    server_id: str, access: str, target_field='server_id',
) -> QuerySet[M]:
    if issubclass(q, Model):
        q = q.objects
    get_ctx(req, logout=False).assert_access(access, server_id)
    return q.filter(**{f'{target_field}__exact': server_id}).all()
