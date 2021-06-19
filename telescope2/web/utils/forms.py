# forms.py
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

import copy
from typing import Any, Callable, Dict, Generic, Optional, Type, TypeVar

from django.db import models
from django.forms import fields, widgets
from django.urls import reverse
from django.utils.safestring import mark_safe

from telescope2.utils.collection import merge_collections
from telescope2.utils.importutil import objpath

from .templates import domtokenlist, optional_attr

WidgetType = TypeVar('WidgetType', bound=widgets.Widget)
T = TypeVar('T', bound=models.Model)


class WidgetSubstitute:
    mapping: Dict[Type[WidgetType], Type[WidgetType]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        for c in cls.mro()[1:]:
            if issubclass(c, widgets.Input):
                cls.mapping[c] = cls
                break


class AttributeInject:
    base_attrs = {}

    def __init__(self, *args, **kwargs) -> None:
        self._attrs = copy.deepcopy(self.base_attrs)
        super().__init__(*args, **kwargs)

    @property
    def attrs(self):
        return self._attrs

    @attrs.setter
    def attrs(self, v):
        self._attrs = merge_collections(v, self._attrs)


class FormConstants:
    SUFFIX = ''

    @property
    def label_suffix(self):
        return self.SUFFIX

    @label_suffix.setter
    def label_suffix(self, v):
        return


class TextInput(AttributeInject, widgets.TextInput, WidgetSubstitute):
    base_attrs = {'class': 'form-control'}


class SwitchInput(AttributeInject, widgets.CheckboxInput):
    base_attrs = {'class': 'form-check-input'}


class AsyncFormMixin(Generic[T]):
    instance: T

    async_writable: bool = False

    @property
    def mutation_endpoint(self):
        return reverse('web:api.mutation', kwargs={'schema': objpath(type(self)), 'item_id': self.instance.pk})

    def user_tests(self, req) -> bool:
        return True

    save: Callable[[bool], T]


def find_widgets(model: Type[models.Model]) -> Dict[str, WidgetType]:
    mapping: Dict[str, WidgetType] = {}
    for f in model._meta.fields:
        if not isinstance(f, models.Field):
            continue
        formfield = f.formfield()
        if not formfield:
            continue
        widget = formfield.widget
        substitute = WidgetSubstitute.mapping.get(type(widget))
        mapping[f.name] = substitute or widget
    return mapping


def gen_labels(model: Type[models.Model], transform=str.lower):
    labels = {}
    for f in model._meta.fields:
        labels[f.name] = transform(f.verbose_name)
    return labels


def identity_field(model: Type[models.Model]):
    field: fields.Field = model._meta.pk.formfield()
    if not field:
        field = fields.CharField(required=True, widget=widgets.HiddenInput(), disabled=True)
    return field


class D3SelectWidget(widgets.Widget):
    template_name = 'telescope2/web/elements/item-list.html'

    def __init__(self, endpoint: str, selection: str, container_id='', classes='',
                 prefix='-',
                 placeholder='Start typing ...', attrs: Optional[Dict] = None):
        super().__init__(attrs=attrs)
        self.id = container_id
        self.classes = classes
        self.endpoint = endpoint
        self.selection = selection
        self.prefix = prefix
        self.placeholder = placeholder

    @property
    def is_hidden(self) -> bool:
        return False

    def get_context(self, name: str, value: Any, attrs: Optional[Dict]) -> Dict[str, Any]:
        attrs = self.build_attrs(self.attrs, attrs)
        attrs_str = mark_safe(' '.join([optional_attr(k, v) for k, v in attrs.items()]))
        prefix = mark_safe(f'<span class="input-group-text">{self.prefix}</span>')
        return {
            'template_name': self.template_name,
            'container_id': optional_attr('id', self.id),
            'classes': optional_attr('class', domtokenlist('d3-item-list', self.classes)),
            'required': optional_attr('required', self.is_required),
            'name': optional_attr('name', name),
            'value': optional_attr('value', self.format_value(value)),
            'attrs': attrs_str,
            'endpoint': self.endpoint,
            'type': self.selection,
            'prefix': prefix,
            'placeholder': self.placeholder,
            'autoclose': 'outside' if self.selection == 'multiple' else 'true',
        }
