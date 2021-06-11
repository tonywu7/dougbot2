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
from typing import Dict, Type, TypeVar

from django.db import models
from django.forms import ModelForm, fields, widgets
from django.urls import reverse

from telescope2.utils.collection import merge_collections
from telescope2.utils.importutil import objpath

WidgetType = TypeVar('WidgetType', bound=widgets.Widget)


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


class AsyncModelForm(ModelForm):
    @property
    def mutation_endpoint(self):
        return reverse('web.api.mutation', kwargs={'schema': objpath(type(self)), 'item_id': self.instance.pk})


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
