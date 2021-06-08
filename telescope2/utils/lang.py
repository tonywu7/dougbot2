# lang.py
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

from typing import Dict, Type

import inflect
from django.db.models import Model

inflection = inflect.engine()


def autoverbose(name: str) -> Dict[str, str]:
    singular = inflection.singular_noun(name)
    if singular:
        name = singular
    return {
        'verbose_name': name,
        'verbose_name_plural': inflection.plural_noun(name),
    }


def pluralize(count: int, term: str) -> str:
    return inflection.plural_noun(term, count)


def plural_clause(count: int, term: str, verb: str) -> str:
    term = pluralize(count, term)
    return f'{term} {inflection.plural_verb(verb, count)}'


def coord_conj(*terms: str, conj='and', oxford=True) -> str:
    if not terms:
        return ''
    if len(terms) == 1:
        return terms[0]
    if len(terms) == 2:
        return f'{terms[0]} {conj} {terms[1]}'
    if oxford:
        oxford = ','
    return f'{", ".join(terms[:-1])}{oxford} {conj} {terms[-1]}'


def pluralize_model(count: int, model: Type[Model]) -> str:
    if count == 1:
        return f'{count} {model._meta.verbose_name}'
    else:
        return f'{count} {model._meta.verbose_name_plural}'
