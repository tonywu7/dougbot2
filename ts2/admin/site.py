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

import logging
from importlib import import_module
from typing import Iterable, Tuple

from django.contrib import auth
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth import admin as auth_admin
from django.core.exceptions import PermissionDenied
from django.db.models import Field
from django.http import HttpRequest, JsonResponse

log = logging.getLogger('django_admin.control')


class BetterAutocompleteJsonView(AutocompleteJsonView):
    def get(self, request: HttpRequest, *args, **kwargs) -> JsonResponse:
        """
        Return a JsonResponse with search results of the form:
        {
            results: [{id: "123" text: "foo"}],
            pagination: {more: true}
        }
        """
        self.term, self.model_admin, self.source_field, to_field_name = self.process_request(request)

        if not self.has_perm(request):
            raise PermissionDenied

        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return JsonResponse({
            'results': [
                {'id': str(getattr(obj, to_field_name)), 'text': str(obj)}
                for obj in context['object_list']
            ],
            'pagination': {'more': context['page_obj'].has_next()},
        })

    def process_request(self, request: HttpRequest) -> Tuple[str, ModelAdmin, Field, str]:
        return super().process_request(request)


class StandardAdminSite(AdminSite):
    def __init__(self, site_name: str) -> None:
        self.site_title = self.site_header = site_name
        super().__init__()

    def autocomplete_view(self, request):
        return BetterAutocompleteJsonView.as_view(admin_site=self)(request)


def create_admin_site(site_name: str, admin_modules: Iterable[str]):
    admin_site = StandardAdminSite(site_name)

    admin_site.register(auth.models.User, auth_admin.UserAdmin)
    admin_site.register(auth.models.Group, auth_admin.GroupAdmin)

    for path in admin_modules:
        admin_module = import_module(path)
        try:
            admin_module.register_all(admin_site)
        except AttributeError:
            pass
        else:
            log.info(f'Registered admin for {admin_module.__name__}')

    return admin_site
