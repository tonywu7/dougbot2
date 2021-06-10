# templates.py
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
from inspect import Parameter, signature
from operator import itemgetter
from typing import Callable, Optional, Tuple, TypeVar

from django import template
from django.template.base import Node, Parser, Token

N = TypeVar('N', bound=Node)
NodeFactory = Callable[..., N]

# Match valid alphanumeric python identifiers
IDENTIFIER = r'[A-Za-z_][A-Za-z0-9]*'

# Match int and float
NUMBERS = r'-?[0-9]*.?[0-9]+'
# Match the 3 constants available in template contexts
LITERALS = r'True|False|None'
# Match a quoted string (assumes properly segmented by Token.split_contents())
QUOTED_STR = r"""(?P<lquote>['"]).*(?P=lquote)"""

ARGS = re.compile(rf'((?P<num>{NUMBERS})|(?P<lit>{LITERALS})|(?P<identifier>{IDENTIFIER})|(?P<str>{QUOTED_STR}))')
KWARGS = re.compile(rf'^(?P<keyword>{IDENTIFIER})=(?P<value>.+)')


def parse_token(token: str) -> Tuple[str | None, template.Variable]:
    kwarg = KWARGS.fullmatch(token)
    if kwarg:
        keyword = kwarg['keyword']
        value = kwarg['value']
    else:
        arg = ARGS.fullmatch(token)
        if arg:
            keyword = None
            value = arg[0]
        else:
            raise template.TemplateSyntaxError(f'Malformed token {repr(token)}')
    value = template.Variable(value)
    return keyword, value


def _is_vararg(p: Parameter):
    return p.kind is Parameter.VAR_POSITIONAL


def _positional_only(p: Parameter):
    return p.kind is Parameter.POSITIONAL_ONLY


def _maybe_positional(p: Parameter):
    return p.kind in (Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD)


def _keyword_only(p: Parameter):
    return p.kind is Parameter.KEYWORD_ONLY


def _may_be_keyword(p: Parameter):
    return p.kind in (Parameter.POSITIONAL_OR_KEYWORD, Parameter.KEYWORD_ONLY)


def register_autotag(library: template.Library, start: str, end: Optional[str] = None) -> Callable[[Parser, Token], N]:
    def wrap(func: NodeFactory):
        sig = signature(func)

        paramdict = sig.parameters
        paramlist = [*sig.parameters.values()]

        types = {p.kind for p in paramlist}
        accepts_args = Parameter.VAR_POSITIONAL in types
        accepts_kwargs = Parameter.VAR_KEYWORD in types

        if end and (not paramlist or paramlist[0].name != 'nodelist'):
            raise TypeError(f'{func} must accept a `nodelist` as its first argument for it to accept an end tag.')

        positional = [p.name for p in paramlist if _maybe_positional(p)]
        if positional:
            positional = itemgetter(*positional)
        else:
            positional = lambda *args: ()  # noqa: E731
        keywords = [p.name for p in paramlist if _keyword_only(p)]

        @library.tag(start)
        def parse(parser: Parser, token: Token) -> N:

            has_keywords = False

            values = {p.name: p.default for p in paramlist}
            if accepts_args:
                values['args'] = []
            if accepts_kwargs:
                values['kwargs'] = {}

            if end:
                values['nodelist'] = parser.parse((end,))
                parser.delete_first_token()
                pos = 1
            else:
                pos = 0

            tag_name, *parts = token.split_contents()

            for part in parts:
                keyword, value = parse_token(part)

                if keyword in ('args', 'kwargs'):
                    raise template.TemplateSyntaxError(
                        f'Forbidden keyword argument name "{keyword}"',
                    )

                if keyword:
                    has_keywords = True
                    par = paramdict.get(keyword)
                    if not par:
                        if not accepts_kwargs:
                            raise template.TemplateSyntaxError(
                                f'{func} does not accept **kwargs',
                            )
                        values['kwargs'][keyword] = value
                        continue
                    if par.kind is Parameter.POSITIONAL_ONLY:
                        raise template.TemplateSyntaxError(
                            f'{keyword} is a positional-only '
                            'argument and cannot be assigned '
                            f'with {repr(part)}',
                        )
                    values[keyword] = value
                    continue

                if has_keywords:
                    raise template.TemplateSyntaxError(
                        'Positional argument found after keyword arguments',
                    )
                par = paramlist[pos]
                if _keyword_only(par):
                    raise template.TemplateSyntaxError(
                        f'{keyword} is a keyword-only '
                        'argument and cannot be assigned '
                        f'with {repr(part)}',
                    )
                if _is_vararg(par):
                    values['args'].append(value)
                else:
                    values[par.name] = value
                    pos += 1

            for k, v in values.items():
                if isinstance(v, Parameter.empty):
                    raise template.TemplateSyntaxError(f'Argument {repr(k)} required')

            args = [*positional(values), *values.get('args', [])]
            kwargs = {**{k: values[k] for k in keywords}, **values.get('kwargs', {})}

            return func(*args, **kwargs)
        return func
    return wrap
