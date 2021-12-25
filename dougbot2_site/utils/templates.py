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

from __future__ import annotations

import ast
import itertools
import re
from collections.abc import Callable
from inspect import Parameter, signature
from operator import itemgetter
from typing import Any, Optional, TypeVar

from django import template
from django.template.base import Node, Parser, Token
from django.utils.html import escape
from django.utils.safestring import mark_safe
from more_itertools import always_iterable

T = TypeVar('T')
N = TypeVar('N', bound=Node)
NodeFactory = Callable[..., N]

# Match valid alphanumeric python identifiers
IDENTIFIER = r'(?:[A-Za-z_][A-Za-z0-9_]*\.)*[A-Za-z_][A-Za-z0-9_]*'

# Match int and float
NUMBERS = r'-?[0-9]*.?[0-9]+'
# Match the 3 constants available in template contexts
LITERALS = r'True|False|None'
# Match a quoted string (assumes properly segmented by Token.split_contents())
QUOTED_STR = r"""(?P<lquote>['"]).*(?P=lquote)"""

ARGS = re.compile(rf'((?P<num>{NUMBERS})|(?P<lit>{LITERALS})|(?P<identifier>{IDENTIFIER})|(?P<str>{QUOTED_STR}))')
KWARGS = re.compile(rf'^(?P<keyword>{IDENTIFIER})=(?P<value>.+)')


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


def assert_valid_identifier(s: str):
    """Make sure the string could be a legal Python identifier."""
    if not s:
        raise ValueError('Identifier cannot be empty')
    try:
        expr: ast.Expression = ast.parse(s).body[0]
    except SyntaxError as e:
        raise ValueError(f'Malformed identifier {repr(s)}') from e
    if not isinstance(expr.value, ast.Name):
        raise ValueError(f'{repr(s)} is not a valid identifier')


def unpack_attributes(node: ast.Attribute):
    """Convert an AST attribute to its string representation and return it.

    Result can be used to initialize a Django template Variable object.
    """
    if isinstance(node.value, ast.Attribute):
        return f'{unpack_attributes(node.value)}.{node.attr}'
    elif isinstance(node.value, ast.Name):
        return f'{node.value.id}.{node.attr}'
    else:
        raise ValueError(node.value)


def create_tag_parser(library: template.Library, start: str, end: Optional[str] = None):
    """Create a Django template tag parser from the callable it decorates.

    The resulting parser optionally supports parsing enclosing blocks,
    which Django's simple tag creator currently doesn't support.

    :param library: The template library to register the parser to
    :type library: template.Library
    :param start: The starting tag to use
    :type start: str
    :param end: The ending tag to use, if the parser should support parsing
    an enclosing template block, defaults to None
    :type end: Optional[str], optional
    """
    if not start:
        raise ValueError('Tag cannot be empty')

    assert_valid_identifier(start)
    if end:
        assert_valid_identifier(end)

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
            expr = f'{tag_name}({", ".join(parts)})'
            try:
                func_call: ast.Call = ast.parse(expr).body[0].value
                assert isinstance(func_call, ast.Call)
            except (SyntaxError, AssertionError) as e:
                raise template.TemplateSyntaxError(
                    f'Malformed function call expression `{expr}` '
                    f'generated from {token}',
                ) from e

            def raise_unsupported(node: ast.AST):
                raise template.TemplateSyntaxError(
                    f'Unsupported {type(node).__name__} expression '
                    f'{expr[node.col_offset:node.end_col_offset]}',
                )

            def convert_expr(node: ast.AST):
                if isinstance(node, ast.Constant):
                    val = node.value
                elif isinstance(node, ast.Name):
                    val = template.Variable(node.id)
                elif isinstance(node, ast.Attribute):
                    val = template.Variable(unpack_attributes(node))
                else:
                    raise_unsupported(node)
                return val

            for param, arg in zip(paramlist[pos:], func_call.args):
                if param.name not in values and accepts_args:
                    raise template.TemplateSyntaxError(
                        f'{func} does not accept additional arguments',
                    )
                val = convert_expr(arg)
                if param.name not in values:
                    values['args'].append(val)
                elif _keyword_only(param):
                    raise template.TemplateSyntaxError(
                        f'{param.name} is a keyword-only argument',
                    )
                else:
                    values[param.name] = val

            for kwarg in func_call.keywords:
                k = kwarg.arg
                if k in ('args', 'kwargs'):
                    raise template.TemplateSyntaxError(
                        f'Forbidden keyword argument name "{k}"',
                    )
                if k not in values and not accepts_kwargs:
                    raise template.TemplateSyntaxError(
                        f'{func} does not accept additional keyword arguments',
                    )
                val = convert_expr(kwarg.value)
                param = paramdict.get(k)
                if param:
                    if _positional_only(param):
                        raise template.TemplateSyntaxError(
                            f'{param.name} is a keyword-only argument',
                        )
                    values[k] = val
                else:
                    values['kwargs'][k] = val

            for k, v in values.items():
                if isinstance(v, Parameter.empty):
                    raise template.TemplateSyntaxError(f'Argument {repr(k)} required')

            args = [*always_iterable(positional(values)), *values.get('args', [])]
            kwargs = {**{k: values[k] for k in keywords}, **values.get('kwargs', {})}

            return func(*args, **kwargs)
        return func
    return wrap


def domtokenlist(*tokens: str):
    """Create a DOMTokenList (space-separated items) from a list of strings."""
    return ' '.join(itertools.chain.from_iterable(t.split(' ') for t in filter(None, tokens) if t)).strip()


def domtokenstr(tokens: str):
    """Parse and reformat a space-separated string of items into a well-formated DOMTokenList."""
    return ' '.join([t for t in tokens.split(' ') if t]).strip()


def unwrap(context: template.Context, maybe_var: T) -> T:
    """Retrieve the value of a Django template Variable.

    If the passed-in object is not a Variable, return it unchanged.
    """
    if isinstance(maybe_var, template.Variable):
        return maybe_var.resolve(context)
    return maybe_var


def optional_attr(attr: str, value: Optional[Any]):
    """Include the attribute `attr` only if `value` has any value.

    Prevents falsy values from being coerced into a string and included
    in the attributes for an HTML tag.
    """
    if value is True:
        return mark_safe(attr)
    elif value:
        return mark_safe(f'{attr}="{escape(value)}"')
    return mark_safe('')
