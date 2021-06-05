# filters.py
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

from typing import Optional, Type

from django.contrib.admin import ModelAdmin, SimpleListFilter
from django.db.models import QuerySet
from django.http import HttpRequest


def boolean_filter(attrib: str, query: str, *, title: Optional[str] = None,
                   yes='Yes', no='No') -> Type[SimpleListFilter]:
    title = title or attrib

    def lookups(self: SimpleListFilter, request: HttpRequest, model_admin: ModelAdmin):
        return [('1', yes), ('0', no)]

    def queryset(self: SimpleListFilter, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        return queryset.filter(**{f'{attrib}__exact': self.value() == '1'})

    def choices(self: SimpleListFilter, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == str(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }

    __dict__ = {
        'title': title,
        'parameter_name': query,
        'lookups': lookups,
        'queryset': queryset,
        'choices': choices,
    }
    return type(f'{SimpleListFilter.__name__}_{attrib}', (SimpleListFilter,), __dict__)
