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
