# base.py
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

from contextlib import contextmanager
from functools import cached_property, wraps
from importlib import import_module
from pathlib import Path
from typing import List, Optional, Tuple, Type, TypedDict, TypeVar, Union

from django.apps import apps
from django.contrib.admin import AdminSite, ModelAdmin, SimpleListFilter
from django.contrib.admin.sites import AlreadyRegistered
from django.db import models
from django.db.models import fields
from django.http import HttpRequest

from telescope2.management.utils import AdminRegistrar
from telescope2.utils.importutil import iter_module_tree

T = TypeVar('T', bound=models.Model)
C = TypeVar('C', bound=ModelAdmin)

ListFilterSpec = List[Tuple[str, Optional[Type[SimpleListFilter]]]]


class FieldsetOptions(TypedDict):
    fields: List[Union[str, Tuple[str, ...]]]
    classes: List[str]
    description: str


class ListEditableTogglePseudoFilter(SimpleListFilter):
    title = 'inline editing'
    parameter_name = '_inline_editable'

    def lookups(self, request: HttpRequest, model_admin: ModelAdmin) -> List[Tuple[str, str]]:
        return [
            ('1', 'enabled'),
            ('0', 'disabled'),
        ]

    def queryset(self, request: HttpRequest, queryset: models.QuerySet) -> Optional[models.QuerySet]:
        return queryset

    def choices(self, changelist):
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == str(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}),
                'display': title,
            }


class SearchMixin:
    model: Type[T]

    @cached_property
    def search_fields(self) -> List[str]:
        textual = []
        target_fields = (
            fields.UUIDField, fields.CharField,
            fields.TextField, fields.IntegerField,
        )
        for f in self.model._meta.get_fields():
            if isinstance(f, target_fields):
                textual.append(f.name)
        return textual

    @cached_property
    def autocomplete_fields(self) -> List[str]:
        related = []
        for f in self.model._meta.get_fields():
            if f.is_relation and f.editable and not f.auto_created:
                related.append(f.name)
        return related


class AdminController(SearchMixin, ModelAdmin):
    model: Type[T]

    @property
    def app_label(self):
        return self.model._meta.app_label

    @property
    def model_label(self):
        return self.model._meta.model_name

    @contextmanager
    def set_current_request(self, request: HttpRequest):
        try:
            self._current_request = request
            yield
        finally:
            del self._current_request

    @property
    def current_request(self) -> Optional[HttpRequest]:
        try:
            return self._current_request
        except AttributeError:
            return None

    def next_object_id(self, object_id):
        pk = self.model._meta.pk.name
        value = self.model.objects.filter(**{f'{pk}__gt': object_id}).order_by(pk).values(pk).first()
        return value and value[pk]

    def prev_object_id(self, object_id):
        pk = self.model._meta.pk.name
        value = self.model.objects.filter(**{f'{pk}__lt': object_id}).order_by(pk).values(pk).last()
        return value and value[pk]

    def intercept_request(f):
        @wraps(f)
        def wrapper(self, request, *args, **kwargs):
            with self.set_current_request(request):
                return f(self, request, *args, **kwargs)
        return wrapper

    @intercept_request
    def changelist_view(self, *args, **kwargs):
        return super().changelist_view(*args, **kwargs)

    @intercept_request
    def change_view(self, *args, object_id, **kwargs):
        extra_context = kwargs.get('extra_context', {})
        extra_context['prev_object_id'] = self.prev_object_id(object_id)
        extra_context['next_object_id'] = self.next_object_id(object_id)
        kwargs['extra_context'] = extra_context
        return super().change_view(*args, object_id=object_id, **kwargs)

    @cached_property
    def _editable_fields(self) -> Tuple[List[str], List[str]]:
        properties = []
        relations = []
        for field in self.model._meta.get_fields():
            if not field.editable or field.auto_created:
                continue
            if field.is_relation:
                if not field.many_to_many or field.remote_field.through._meta.auto_created:
                    relations.append(field.name)
            else:
                properties.append(field.name)
        return properties, relations

    @cached_property
    def list_display(self) -> List[str]:
        sortable = ['id']
        target_fields = (
            fields.CharField, fields.TextField,
            fields.IntegerField, fields.DateField,
            fields.DateTimeField, fields.URLField,
        )
        for f in self.model._meta.get_fields():
            if f.editable and not f.auto_created and type(f) in target_fields:
                sortable.append(f.name)
        return sortable

    @property
    def list_editable(self) -> List[str]:
        if not self.current_request:
            return []
        editable = self.current_request.GET.get('_inline_editable', '0')
        if editable != '1':
            return []
        properties, relations = self._editable_fields
        return [p for p in properties if p in self.list_display]

    def _auto_list_filters(self) -> ListFilterSpec:
        target_fields = (
            fields.BooleanField, fields.DateField,
            fields.DateTimeField, fields.IntegerField,
        )
        filterable = []
        for f in self.model._meta.get_fields():
            if not f.auto_created and type(f) in target_fields:
                filterable.append((f.name, None))
        return filterable

    def _finalize_filters(self, filters: ListFilterSpec):
        return [k if v is None else (k, v) for k, v in filters]

    def _list_filters(self) -> ListFilterSpec:
        return [
            (ListEditableTogglePseudoFilter, None),
            *self._auto_list_filters(),
        ]

    @cached_property
    def list_filter(self):
        return self._finalize_filters(self._list_filters())

    @cached_property
    def exclude(self) -> List[str]:
        return []


class BaseModelAdmin(AdminController, ModelAdmin):
    pass


def register_all_defined(self: AdminSite, registrar: AdminRegistrar):
    for path in iter_module_tree(str(Path(__file__).with_name('views')), depth=2):
        import_module(f'.views.{".".join(path)}', __package__)
    registrar.apply_all(self)


def register_all_default(self: AdminSite, app_name: str, base=ModelAdmin):
    models = apps.get_app_config(app_name).get_models()
    for m in models:
        try:
            self.register(m, base)
        except AlreadyRegistered:
            continue
