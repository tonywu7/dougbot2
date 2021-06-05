# __init__.py
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

import logging
from importlib import import_module
from pathlib import Path
from typing import Tuple

from django.contrib import auth
from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth import admin as auth_admin
from django.core.exceptions import PermissionDenied
from django.db.models import Field
from django.http import HttpRequest, JsonResponse

from telescope2.utils.importutil import iter_module_tree

log = logging.getLogger('telescope2.control')


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
    site_title = site_header = 'telescope2 console'

    def autocomplete_view(self, request):
        return BetterAutocompleteJsonView.as_view(admin_site=self)(request)


admin_site = StandardAdminSite()

admin_site.register(auth.models.User, auth_admin.UserAdmin)
admin_site.register(auth.models.Group, auth_admin.GroupAdmin)

for path in iter_module_tree(str(Path(__file__).parent.parent), depth=2):
    if len(path) == 2 and path[-1] == 'admin':
        admin_module = import_module(f'..{".".join(path)}', __package__)
        try:
            admin_module.register_all(admin_site)
        except AttributeError:
            pass
        else:
            log.info(f'Registered admin for {admin_module.__name__}')
