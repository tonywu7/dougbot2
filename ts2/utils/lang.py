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

from __future__ import annotations

import re

import inflect
import unidecode
from django.db.models import Model

inflection = inflect.engine()


def autoverbose(name: str) -> dict[str, str]:
    singular = inflection.singular_noun(name)
    if singular:
        name = singular
    return {
        'verbose_name': name,
        'verbose_name_plural': inflection.plural_noun(name),
    }


def pluralize(count: int, term: str) -> str:
    return inflection.plural_noun(term, count)


def singularize(term: str) -> str:
    return inflection.singular_noun(term) or term


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


def either_or(*terms: str, sep=', ') -> str:
    if not terms:
        return ''
    if len(terms) == 1:
        return terms[0]
    if len(terms) == 2:
        return f'either {terms[0]} or {terms[1]}'
    sep = f'{sep}or '
    return f'either {sep.join(terms)}'


def pluralize_model(count: int, model: type[Model]) -> str:
    if count == 1:
        return f'{count} {model._meta.verbose_name}'
    else:
        return f'{count} {model._meta.verbose_name_plural}'


def pl_cat_attributive(category: str, terms: list[str], sep=' ', conj='and') -> str:
    return f'{pluralize(len(terms), category)}{sep}{coord_conj(*terms, conj=conj)}'


def pl_cat_predicative(category: str, terms: list[str], sep=' ', conj='and') -> str:
    return f'{coord_conj(*terms, conj=conj)}{sep}{pluralize(len(terms), category)}'


class QuantifiedNP:
    def __init__(self, *nouns, concise: str = None, attributive: str = '',
                 predicative: str = '', conjunction: str = 'or', definite=False):
        if not nouns:
            raise ValueError('One or more noun terms required')

        self._kwargs = {
            'nouns': nouns,
            'concise': concise,
            'attributive': attributive,
            'predicative': predicative,
            'conjunction': conjunction,
            'definite': definite,
        }
        self.definite = definite

        if concise is None:
            concise = nouns[0]
        self.concise_singular = inflection.singular_noun(concise) or concise
        self.concise_plural = inflection.plural(concise)

        self.predicative = predicative.strip()
        if self.predicative:
            self.predicative = f', {self.predicative}'
        attributive = attributive.strip()
        if attributive:
            self.attr_singular = f'{attributive} '
            self.attr_plural = f'{inflection.plural_adj(attributive)} '
        else:
            self.attr_singular = ''
            self.attr_plural = ''
        self.nouns_singular = coord_conj(*[inflection.singular_noun(n) or n for n in nouns], conj=conjunction)
        self.nouns_plural = coord_conj(*[inflection.plural(n) for n in nouns], conj=conjunction)

    def _formatted(self, prefix: str, attr: str, noun: str, pred: str):
        return f'{prefix}{attr}{noun}{pred}'

    def concise(self, num: int):
        if num > 1:
            return self.concise_plural
        return self.concise_singular

    def a(self):
        term = f'{self.attr_singular}{self.nouns_singular}'
        if self.definite:
            art = 'the'
        else:
            art = inflection.a(self.attr_singular or self.nouns_singular).split(' ')[0]
        return f'{art} {term}{self.predicative}'

    def one(self):
        return f'one {self.attr_singular}{self.nouns_singular}{self.predicative}'

    def one_of(self):
        return f'one of {self.attr_singular}{self.nouns_singular}{self.predicative}'

    def no(self):
        return f'no {self.attr_singular}{self.nouns_singular}{self.predicative}'

    def zero_or_more(self):
        return f'zero or more {self.attr_plural}{self.nouns_plural}{self.predicative}'

    def one_or_more(self):
        return f'one or more {self.attr_plural}{self.nouns_plural}{self.predicative}'

    def some(self):
        return f'some {self.attr_singular}{self.nouns_singular}{self.predicative}'

    def bare(self):
        return f'{self.attr_singular}{self.nouns_singular}'

    def bare_pl(self):
        return f'{self.attr_plural}{self.nouns_plural}'

    def __or__(self, other: QuantifiedNP) -> QuantifiedNP:
        if not isinstance(other, QuantifiedNP):
            return NotImplemented
        if (not self.nouns_singular == other.nouns_singular
                or not self.predicative == other.predicative
                or any((self.definite, other.definite))):
            return QuantifiedNPS(self, other)
        kwargs = {}
        kwargs['concise'] = coord_conj(self._kwargs['concise'], other._kwargs['concise'], conj='or')
        kwargs['attributive'] = coord_conj(self._kwargs['attributive'], other._kwargs['attributive'], conj='or')
        kwargs['predicative'] = self._kwargs['predicative']
        kwargs['conjunction'] = self._kwargs['conjunction']
        item = QuantifiedNP(*self._kwargs['nouns'], **kwargs)
        item.concise_plural = coord_conj(inflection.plural(self._kwargs['concise']),
                                         inflection.plural(other._kwargs['concise']),
                                         conj='or')
        item.attr_plural = coord_conj(inflection.plural_adj(self._kwargs['attributive']),
                                      inflection.plural_adj(other._kwargs['attributive']),
                                      conj='or') + ' '
        return item

    def __repr__(self):
        return f'<Quantified noun phrase: {self.nouns_singular}>'


class QuantifiedNPS(QuantifiedNP):
    def __init__(self, *phrases: QuantifiedNP):
        self.phrases = phrases

    def concise(self, num: int):
        if num > 1:
            return self.bare_pl()
        return self.bare()

    def a(self):
        return inflection.a(self.bare())

    def one(self):
        return f'one {self.bare()}'

    def one_of(self):
        return f'one of {self.bare()}'

    def no(self):
        return f'no {self.bare()}'

    def zero_or_more(self, conj='or'):
        terms = [p.concise(2) for p in self.phrases]
        return f'zero or more {coord_conj(*terms, conj=conj)}'

    def one_or_more(self, conj='or'):
        terms = [p.concise(2) for p in self.phrases]
        return f'one or more {coord_conj(*terms, conj=conj)}'

    def some(self, conj='or'):
        terms = [p.concise(1) for p in self.phrases]
        return f'some {coord_conj(*terms, conj=conj)}'

    def bare(self, conj='or'):
        return coord_conj(*[p.concise(1) for p in self.phrases], conj=conj)

    def bare_pl(self, conj='or'):
        return coord_conj(*[p.concise(2) for p in self.phrases], conj=conj)

    def __iter__(self):
        yield from self.phrases

    def flattened(self):
        for phrase in self.phrases:
            if isinstance(phrase, QuantifiedNPS):
                yield from phrase
            else:
                yield phrase

    def __or__(self, other: QuantifiedNP | QuantifiedNPS) -> QuantifiedNPS:
        if not isinstance(other, QuantifiedNP):
            return NotImplemented
        phrases = [*self.phrases]
        if isinstance(other, QuantifiedNPS):
            phrases.extend(other.phrases)
        else:
            phrases.append(other)
        return QuantifiedNPS(*phrases)


def slugify(name: str, sep='-', *, limit=0) -> str:
    t = re.sub(r'[\W_]+', sep, str(unidecode.unidecode(name))).strip(sep).lower()
    if limit > 0:
        t = sep.join(t.split(sep)[:limit])
    return t
