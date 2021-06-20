# mutation.py
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

from __future__ import annotations

from typing import Dict, Type

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.module_loading import import_string
from django.views.decorators.http import require_POST

from ..utils.forms import AsyncFormMixin


def error_response(reason: str | Dict, status: int = 400):
    if isinstance(reason, Dict):
        errors = []
        for k, v in reason.items():
            for e in v:
                errors.append(f'{k}: {e}')
        reason = '\n'.join(errors)
    return JsonResponse(data={'status': status, 'error': reason}, status=status)


@require_POST
@login_required
def async_form_save(req: HttpRequest, schema: str, item_id: str, guild_id: str) -> HttpResponse:
    try:
        form_cls: Type[AsyncFormMixin] = import_string(schema)
        assert issubclass(form_cls, AsyncFormMixin)
        assert form_cls.async_writable
    except (ImportError, AssertionError):
        raise SuspiciousOperation(f'Unknown form schema {schema}')

    item = get_object_or_404(form_cls._meta.model, pk=item_id)

    form = form_cls(data=req.POST, instance=item)
    if not form.user_tests(req):
        raise PermissionDenied()

    if not form.is_valid():
        return error_response(form.errors)

    try:
        form.save()
    except ValueError as e:
        return error_response(str(e))

    return HttpResponse(status=204)
