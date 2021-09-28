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

"""Natural language utilities."""

from __future__ import annotations

import re
from functools import cache
from typing import Optional, TypedDict

from discord import User
from discord.ext.commands import BucketType, Context
from discord.ext.commands.view import StringView

from ...utils.markdown import tag
from ._compat import engine_

inflection = engine_()

BUCKET_DESCRIPTIONS = {
    BucketType.default: 'globally',
    BucketType.user: 'per user',
    BucketType.member: 'per user',
    BucketType.guild: 'per server',
    BucketType.channel: 'per channel',
    BucketType.category: 'per channel category',
    BucketType.role: 'per role',
}


def pluralize(count: int, term: str) -> str:
    """Return the plural version of `term`."""
    return inflection.plural_noun(term, count)


def singularize(term: str) -> str:
    """Return the singular version of `term`.

    If `term` is already singular, return it as-is.
    """
    return inflection.singular_noun(term) or term


def plural_clause(count: int, term: str, verb: str) -> str:
    """Return a plural number version of this noun phrase."""
    term = pluralize(count, term)
    return f'{term} {inflection.plural_verb(verb, count)}'


def coord_conj(*terms: str, conj='and', oxford=True) -> str:
    """Join multiple terms together as a coordinating conjunction.

    :Example:

    .. code-block::

        >>> coord_conj("apple", "orange", "banana")
        ... 'apple, orange, and banana'
        >>> coord_conj("apple", "orange", "banana", oxford=False)
        ... 'apple, orange and banana'

    """
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
    """Phrase multiple terms into the expression "either ..., or ..., or ..."."""
    if not terms:
        return ''
    if len(terms) == 1:
        return terms[0]
    if len(terms) == 2:
        return f'either {terms[0]} or {terms[1]}'
    sep = f'{sep}or '
    return f'either {sep.join(terms)}'


def pl_cat_predicative(category: str, terms: list[str], sep=' ', conj='and') -> str:
    """Create an predicative phrase expressing multiple kinds of some category.

    :Example:

    .. code-block::

        >>> pl_cat_predicative("fruit", ["apple", "orange", "banana"], ': ')
        ... 'fruits: apple, orange, and banana'

    """
    return f'{pluralize(len(terms), category)}{sep}{coord_conj(*terms, conj=conj)}'


def pl_cat_attributive(category: str, terms: list[str], sep=' ', conj='and') -> str:
    """Create an attributive phrase expressing multiple kinds of some category.

    :Example:

    .. code-block::

        >>> pl_cat_attributive("apple", ["red", "green", "blue"])
        ... 'red, green, and blue apples'

    """
    return f'{coord_conj(*terms, conj=conj)}{sep}{pluralize(len(terms), category)}'


class QuantifiedNP:
    """Quantified noun phrase."""

    def __init__(self, *nouns, concise: str = None, attributive: str = '',
                 predicative: str = '', conjunction: str = 'or',
                 definite=False, uncountable=False):
        if not nouns:
            raise ValueError('One or more noun terms required')

        self._kwargs = {
            'nouns': nouns,
            'concise': concise,
            'attributive': attributive,
            'predicative': predicative,
            'conjunction': conjunction,
            'definite': definite,
            'uncountable': uncountable,
        }
        self.uncountable = uncountable
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
        if self.definite and self.uncountable:
            art = ''
        elif self.definite:
            art = 'the '
        elif self.uncountable:
            return self.some()
        else:
            art = inflection.a(self.attr_singular or self.nouns_singular).split(' ')[0] + ' '
        return f'{art} {term}{self.predicative}'

    def one_of(self):
        return f'one of {self.attr_singular}{self.nouns_singular}{self.predicative}'

    def no(self):
        return f'no {self.attr_singular}{self.nouns_singular}{self.predicative}'

    def zero_or_more(self):
        if self.uncountable:
            return self.some()
        return f'zero or more {self.attr_plural}{self.nouns_plural}{self.predicative}'

    def one_or_more(self):
        if self.uncountable:
            return self.some()
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
    """Multiple quantified noun phrases."""

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
    """Convert arbitrary text to a URL-safe, kebab-case string (a slug in publishing).

    :Example:

    .. code-block::

        >>> slugify('at The Times, stories about Mr. Obama generally get one of two names.')
        ... 'at-the-times-stories-about-mr-obama-generally-get-one-of-two-names'

    """
    t = re.sub(r'[\W_]+', sep, str(name).strip(sep).lower()).strip(sep)
    if limit > 0:
        t = sep.join(t.split(sep)[:limit])
    return t


class PartOfSpeech(TypedDict):
    """Pronoun variations based on cases and part-of-speech info."""
    PRP_NOM: str  # Nominative
    PRP_ACC: str  # Accusative
    DET_POSS: str  # Possessive determiner
    PRP_POSS: str  # Possessive pronoun
    PRP_REFL: str  # Reflexive pronoun


_3RD_PERSON_PLURAL: PartOfSpeech = {
    'PRP_NOM': 'they',
    'PRP_ACC': 'them',
    'DET_POSS': 'their',
    'PRP_POSS': 'theirs',
    'PRP_REFL': 'themselves',
}

_2ND_PERSON_SINGULAR: PartOfSpeech = {
    'PRP_NOM': 'you',
    'PRP_ACC': 'you',
    'DET_POSS': 'your',
    'PRP_POSS': 'yours',
    'PRP_REFL': 'yourself',
}


def address(msg: str, person: User, ctx: Optional[Context] = None,
            sentence=True, **infinitives: str) -> str:
    """Formularize a sentence in 2nd person or 3rd person based on the User being addressed\
    and optionally the Context object.

    For example, if the User is not the same as the `author` of the Context,
    this returns a sentence phrased in 3rd-person singular.
    """
    pos: PartOfSpeech
    third_person = not ctx or ctx.author.id != person.id
    if third_person:
        pos = _3RD_PERSON_PLURAL
        entity = tag(person)
    else:
        pos = _2ND_PERSON_SINGULAR
        entity = 'you'
    verbs = {k: inflection.plural_verb(v, 2) for k, v in infinitives.items()}
    phrases = {f'{k}_vp': f'{entity} {inflection.plural_verb(v, int(third_person))}'
               for k, v in infinitives.items()}
    tokens = {**pos, **verbs, **phrases, 'entity': entity}
    msg = msg % tokens
    if sentence:
        msg = msg[0].upper() + msg[1:]
    return msg


def indicate_eol(s: StringView) -> str:
    """Indicate the end of line of a discord.py StringView."""
    return f'{s.buffer[:s.index + 1]} ←'


def indicate_extra_text(s: StringView) -> str:
    """Indicate the portion of a StringView that has not been parsed."""
    return f'{s.buffer[:s.index]} → {s.buffer[s.index:]} ←'


def describe_concurrency(number: int, bucket: BucketType):
    """Describe a concurrency setting in a human-friendly way."""
    bucket_type = BUCKET_DESCRIPTIONS[bucket]
    info = (f'concurrency: maximum {number} {pluralize(number, "call")} '
            f'running at the same time {bucket_type}')
    return info


@cache
def readable_perm_name(p: str) -> str:
    """Modify a discord.py Permissions attribute so that it uses terms\
    on the Discord UI that are more familiar to people."""
    return (
        p.replace('_', ' ')
        .replace('guild', 'server')
        .replace('create instant invite', 'create invite')
        .replace('emoji', 'emote')
        .title()
        .replace('Tts', 'TTS')
    )
