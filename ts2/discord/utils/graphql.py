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

from __future__ import annotations

import re
from typing import Generic, Protocol, TypeVar

from django.db.models import Model, QuerySet
from django.forms import Form, ModelForm
from django.http import HttpRequest
from graphene import (ID, Argument, InputObjectType, List, Mutation, NonNull,
                      ObjectType, String)

T = TypeVar('T', bound=Model)
U = TypeVar('U', bound=Form)


def _rename_to_input(s: str) -> str:
    return re.sub(r'(?:Type)?$', 'Input', s, 1)


def input_from_type(t: type[ObjectType], **overrides) -> type[InputObjectType]:
    """Generate an InputObjectType from an Object."""
    __dict__ = {k: v for k, v in overrides.items() if v}

    for k, v in t._meta.fields.items():
        if overrides.get(k) is False:
            continue
        field_t = v._type
        if isinstance(field_t, List):
            __dict__[k] = List(field_t.of_type)
        else:
            __dict__[k] = v.type()

    return type(_rename_to_input(t.__name__), (InputObjectType,), __dict__)


class ModelMutation(Generic[T], Mutation):
    """Mixin providing methods for working with mutations on Django models."""

    class Meta:
        abstract = True

    def __init_subclass__(cls, **kwargs) -> None:
        try:
            model: type[T] = cls.Meta.model
        except AttributeError:
            super().__init_subclass__(**kwargs)
            return
        cls._model = model
        key = f'{model._meta.model_name}_id'
        try:
            args = cls.Arguments
        except AttributeError:
            class Arguments:
                pass
            cls.Arguments = args = Arguments
        setattr(args, key, Argument(ID, required=True))
        super().__init_subclass__(**kwargs)

    @classmethod
    def get_queryset(cls) -> QuerySet[T]:
        """Get the default queryset of this model."""
        return cls._model.objects.all()

    @classmethod
    def get_instance(cls, req: HttpRequest, item_id: str) -> T:
        """Get the object this mutation applies to."""
        return cls.get_queryset().get(pk=item_id)

    @classmethod
    def mutate(cls, *args, **kwargs):
        """Apply the mutation.

        Subclasses must override this method.
        """
        raise NotImplementedError


class FormMutationMixin(Generic[U]):
    """Mixin providing conversion from a mutation to a Django form."""

    def __init_subclass__(cls, **kwargs) -> None:
        try:
            cls._form = cls.Meta.form
        except AttributeError:
            pass
        super().__init_subclass__(**kwargs)

    @classmethod
    def get_form(cls, arguments: dict, instance=None, raise_invalid=True) -> Form:
        """Create a form using this mutation's form class and arguments."""
        form_cls = cls._form
        kwargs = {'data': arguments}
        if issubclass(form_cls, ModelForm):
            kwargs['instance'] = instance
        form = form_cls(**kwargs)
        if not form.is_valid() and raise_invalid:
            raise ValueError(form.errors.as_ul())
        return form


class HasContext(Protocol):
    """The `info` parameter in graphene callbacks with access to the request context."""

    context: HttpRequest


class KeyValuePairType(ObjectType):
    """Utility type for representing a dictionary with arbitrary keys as a list."""

    key: str = NonNull(String)
    value: str = NonNull(String)

    @classmethod
    def from_dict(cls, record: dict[str, str]) -> list[KeyValuePairType]:
        """Create a list of key-value pairs from a dict."""
        return [KeyValuePairType(str(k), str(v)) for k, v in record.items()]


class KeyValuePairInput(InputObjectType):
    """Key-value pair type as input."""

    key: str = Argument(String, required=True)
    value: str = Argument(String, required=True)

    @classmethod
    def to_dict(cls, kvp: list[KeyValuePairInput]) -> dict[str, str]:
        """Create a dict represented by this list of key-value pairs."""
        return {item.key: item.value for item in kvp}
