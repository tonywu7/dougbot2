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

from contextlib import contextmanager
from functools import cached_property, wraps
from importlib import import_module
from typing import List, Optional, Tuple, Type, TypedDict, TypeVar, Union

from django.apps import apps
from django.contrib.admin import AdminSite, ModelAdmin, SimpleListFilter
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.db import models
from django.db.models import fields
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from polymorphic.admin import PolymorphicChildModelAdmin
from polymorphic.models import PolymorphicModel

from .utils.importutil import iter_module_tree
from .utils.registrar import AdminRegistrar

T = TypeVar('T', bound=models.Model)
U = TypeVar('U', bound=PolymorphicModel)
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
        textual = ['pk']
        target_fields = (
            fields.UUIDField, fields.CharField,
            fields.TextField, fields.IntegerField,
        )
        for f in self.model._meta.get_fields():
            if isinstance(f, target_fields) or f.is_relation and f.one_to_one:
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
        sortable = ['pk']
        target_fields = (
            fields.CharField, fields.TextField,
            fields.IntegerField, fields.DateField,
            fields.DateTimeField, fields.URLField,
            fields.BooleanField, fields.FloatField,
            fields.SlugField,
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
        def _filterable_types(f):
            return type(f) in (
                fields.BooleanField, fields.DateField,
                fields.DateTimeField, fields.IntegerField,
            )

        def _filterable_values(f):
            return (isinstance(f, (fields.TextField, fields.CharField))
                    and f.choices)

        tests = [_filterable_types, _filterable_values]

        filterable = []
        for f in self.model._meta.get_fields():
            if not f.auto_created and any(t(f) for t in tests):
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


class BasePolymorphicAdmin(AdminController, PolymorphicChildModelAdmin):
    def _response_post_save(self, request, obj):
        opts = self.model._meta
        if self.has_view_or_change_permission(request):
            post_url = reverse('admin:%s_%s_changelist' %
                               (opts.app_label, opts.model_name),
                               current_app=self.admin_site.name)
            preserved_filters = self.get_preserved_filters(request)
            post_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, post_url)
        else:
            post_url = reverse('admin:index',
                               current_app=self.admin_site.name)
        return HttpResponseRedirect(post_url)

    def response_post_save_add(self, request, obj):
        return self._response_post_save(request, obj)

    def response_post_save_change(self, request, obj):
        return self._response_post_save(request, obj)


class BaseModelAdmin(AdminController, ModelAdmin):
    pass


def polymorphic_admin(cls: Type[U], *base_classes: Type) -> Type[C]:
    if not issubclass(cls, PolymorphicModel):
        raise TypeError(f'Model {cls} does not inherit from PolymorphicModel')

    try:
        return cls.Meta.child_admin
    except AttributeError:
        pass

    options = getattr(cls, '__admin_args__', {})
    __dict__ = {
        'base_model': cls,
        'show_in_index': True,
        **options,
    }

    admin_cls = type(f'{cls.__name__}Admin', base_classes, __dict__)
    cls.Meta.child_admin = admin_cls
    return admin_cls


def register_all_defined(self: AdminSite, views: str, pkg: str, registrar: AdminRegistrar):
    for path in iter_module_tree(views, depth=2):
        import_module(f'.views.{".".join(path)}', pkg)
    registrar.apply_all(self)


def register_all_polymorphic(self: AdminSite, app_name: str, base_cls: Type[U], *base_classes):
    models = apps.get_app_config(app_name).get_models()
    for m in models:
        if not issubclass(m, base_cls):
            continue
        admin_cls = polymorphic_admin(m, *base_classes)
        try:
            self.register(m, admin_cls)
        except AlreadyRegistered:
            continue


def register_all_default(self: AdminSite, app_name: str, base=ModelAdmin):
    models = apps.get_app_config(app_name).get_models()
    for m in models:
        try:
            self.register(m, base)
        except AlreadyRegistered:
            continue
