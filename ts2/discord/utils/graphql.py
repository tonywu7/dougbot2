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

import re
from contextlib import contextmanager
from typing import Generic, Optional, TypeVar

from django.core.exceptions import BadRequest, ObjectDoesNotExist
from django.db.models import Model, QuerySet
from django.forms import Form, ModelForm
from graphene import ID, Argument, InputObjectType, List, Mutation, ObjectType

T = TypeVar('T', bound=Model)
U = TypeVar('U', bound=Form)


def _rename_to_input(s: str) -> str:
    return re.sub(r'(?:Type)?$', 'Input', s, 1)


def input_from_type(t: type[ObjectType], **overrides) -> type[InputObjectType]:
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
    class Meta:
        abstract = True

    def __init_subclass__(cls, model: Optional[type[T]] = None, **kwargs) -> None:
        if model is None:
            super().__init_subclass__(**kwargs)
            return
        cls._model = model
        try:
            cls.Arguments.id = Argument(ID, required=True)
        except AttributeError:
            class Arguments:
                id = Argument(ID, required=True)
            cls.Arguments = Arguments
        super().__init_subclass__(**kwargs)

    @classmethod
    def get_queryset(cls) -> QuerySet[T]:
        return cls._model.objects.all()

    @classmethod
    def get_instance(cls, arguments: dict) -> T:
        return cls.get_queryset().get(pk=arguments['id'])

    @classmethod
    @contextmanager
    def instance(cls, arguments: dict, save=True):
        try:
            instance = cls.get_instance(arguments)
        except (LookupError, ObjectDoesNotExist):
            raise BadRequest('Instance not found.')
        try:
            yield instance
            if save:
                instance.save()
        finally:
            pass

    @classmethod
    def mutate(cls, *args, **kwargs):
        raise NotImplementedError


class FormMutationMixin(Generic[U]):
    @classmethod
    def get_form(cls, form_cls: type[Form], arguments: dict,
                 instance=None, raise_invalid=True) -> Form:
        kwargs = {'data': arguments}
        if issubclass(form_cls, ModelForm):
            kwargs['instance'] = instance
        form = form_cls(**kwargs)
        if not form.is_valid() and raise_invalid:
            raise ValueError(form.errors.as_ul())
        return form
