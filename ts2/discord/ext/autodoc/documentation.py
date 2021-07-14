# documentation.py
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

import logging
from collections import OrderedDict, deque
from collections.abc import Callable
from functools import cached_property, partial, reduce
from inspect import Parameter
from operator import or_
from typing import Any, Literal, Optional, Union, get_args, get_origin

import attr
import discord
from discord.ext import commands
from discord.ext.commands import Cog, Command, Context, Converter, Greedy
from discord.utils import escape_markdown
from django.utils.text import camel_case_to_spaces
from more_itertools import partition, split_at

from ...utils.duckcord.embeds import Embed2
from ...utils.markdown import a, blockquote, mta_arrow_bracket, pre, strong
from ...utils.pagination import page_embed2, page_plaintext
from .exceptions import BadDocumentation, MissingDescription
from .explanation import readable_perm_name
from .lang import QuantifiedNP, pl_cat_predicative, singularize, slugify

_Converter = Union[Converter, type[Converter]]
_Annotation = Union[type, _Converter]

_AllChannelTypes = Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]
_TextAndVCs = Union[discord.TextChannel, discord.VoiceChannel]

CheckPredicate = Callable[[Context], bool]
CheckWrapper = Callable[[Command], Command]
CheckDecorator = Callable[..., CheckWrapper]

log = logging.getLogger('discord.commands')


_type_descriptions: dict[_Annotation, QuantifiedNP] = {
    int: QuantifiedNP('whole number'),
    float: QuantifiedNP('number', attributive='whole or decimal'),

    str: QuantifiedNP('text'),
    bool: QuantifiedNP('yes or no', concise='yes/no'),

    discord.Member: QuantifiedNP('id', 'name', 'mention', concise='user', attributive="Discord user's"),
    discord.Message: QuantifiedNP('id', 'URL', concise='message', attributive="message's"),
    discord.PartialMessage: QuantifiedNP('id', 'URL', concise='message', attributive="message's"),
    discord.Role: QuantifiedNP('id', 'name', 'mention', concise='role', attributive="role's"),
    discord.TextChannel: QuantifiedNP('id', 'name', concise='text channel', attributive="text channel's"),
    discord.VoiceChannel: QuantifiedNP('id', 'name', concise='voice channel', attributive="voice channel's"),
    discord.Colour: QuantifiedNP('color', predicative='in hexadecimal or RGB format'),
    discord.Emoji: QuantifiedNP('emote', predicative='must be in servers the bot is in'),
    discord.PartialEmoji: QuantifiedNP('emote'),

    _AllChannelTypes: QuantifiedNP('id', 'name', concise='channel', attributive="channel's"),
    Optional[_AllChannelTypes]: QuantifiedNP('id', 'name', concise='channel', attributive="channel's"),
    _TextAndVCs: QuantifiedNP('id', 'name', concise='channel', attributive="channel's"),
    Optional[_TextAndVCs]: QuantifiedNP('id', 'name', concise='channel', attributive="channel's"),
}

_type_converters: list[tuple[_Annotation, Callable[[_Annotation], _Annotation]]] = []


def _record_perm_check(place: str, **perms: bool) -> list[str]:
    denied, allowed = partition(lambda t: t[1], perms.items())
    denied = [strong(readable_perm_name(s)) for s, v in denied]
    allowed = [strong(readable_perm_name(s)) for s, v in allowed]
    msg = []
    if allowed:
        msg.append(f'Requires {pl_cat_predicative("perm", allowed)} in {place}')
    if denied:
        msg.append(f'Denies anyone with {pl_cat_predicative("perm", denied)} in {place}')
    return msg


def _record_owner_check():
    return ["Only the bot's owner can use this command."]


_record_server_perm_check = partial(_record_perm_check, 'server')
_record_channel_perm_check = partial(_record_perm_check, 'channel')

CHECK_TRANSLATOR: dict[CheckDecorator, Callable[..., list[str]]] = {
    commands.has_permissions: _record_channel_perm_check,
    commands.has_guild_permissions: _record_server_perm_check,
    commands.is_owner: _record_owner_check,
}


def _is_type_union(annotation) -> bool:
    return get_origin(annotation) is Union


def _is_literal_type(annotation) -> bool:
    return get_origin(annotation) is Literal


def _is_optional_type(annotation) -> bool:
    return type(None) in get_args(annotation)


def _get_constituents(annotation) -> list[_Annotation]:
    constituents = filter(lambda t: t is not type(None), get_args(annotation))  # noqa: E721
    return [*split_at(constituents, _is_literal_type)][0]


def _get_description(t: _Annotation):
    return _type_descriptions.get(t)


def _get_type_converter(t: type):
    for k, v in _type_converters:
        if (isinstance(t, k)
                or isinstance(t, type)
                and issubclass(t, k)):
            return v


def add_type_description(t: _Annotation, np: QuantifiedNP):
    _type_descriptions[t] = np


def add_type_converter(t: _Annotation, c: Callable[[_Annotation], _Annotation]):
    _type_converters.append((t, c))


@attr.s(eq=True, hash=True)
class Argument:
    key: str = attr.ib(order=False)
    annotation: _Annotation = attr.ib(order=False)
    accepts: QuantifiedNP = attr.ib(order=False)
    greedy: bool = attr.ib(order=False)
    final: bool = attr.ib(order=False)
    default: Any = attr.ib(default=attr.NOTHING, order=False)
    help: str = attr.ib(default='', order=False)

    description: str = attr.ib(default='', order=False)
    node: str = attr.ib(default='', order=False)
    signature: str = attr.ib(default='', order=False)
    order: int = attr.ib(default=0)

    @property
    def is_hidden(self) -> str:
        return self.key[0] == '_'

    @property
    def is_unused(self) -> bool:
        return (self.final and self.is_optional
                and not self.help
                and not self.description)

    @property
    def is_optional(self) -> bool:
        return self.default is not attr.NOTHING

    @cached_property
    def slug(self) -> str:
        return slugify(singularize(self.key))

    def describe(self) -> str:
        if self.description:
            return self.description
        if self.is_unused:
            accepts = 'Extra texts, not used'
        elif self.final:
            accepts = self.accepts.bare_pl()
        elif self.greedy:
            accepts = self.accepts.one_or_more()
        else:
            accepts = self.accepts.a()
        if self.is_optional:
            accepts = f'{accepts}; optional'
            if self.default:
                accepts = f'{accepts}, default is {self.default}'
        if self.help:
            accepts = f'{self.help} Accepts {accepts}'
        else:
            accepts = f'Accepts {accepts}'
        return accepts

    def as_node(self) -> str:
        if self.node:
            return self.node
        if self.is_unused:
            return ''
        if self.final:
            return f'[{self.accepts.concise(2)} ...]'
        if self.greedy:
            return f'[one or more {self.accepts.concise(2)}]'
        return f'[{self.accepts.concise(1)}]'

    def __str__(self):
        if self.signature:
            return self.signature
        if self.is_unused:
            return '[...]'
        if self.final:
            return f'[{self.slug} ...]'
        if self.greedy:
            return f'[{self.slug} {self.slug} ...]'
        if self.is_optional:
            return f'[{self.slug}]'
        return f'‹{self.slug}›'

    def __repr__(self):
        return self.slug

    @classmethod
    def from_parameter(cls, param: Parameter) -> Argument:
        key = param.name
        annotation = param.annotation
        if annotation is Parameter.empty:
            raise BadDocumentation(f'Parameter {param.name} is not annotated')
        default = param.default if param.default is not Parameter.empty else attr.NOTHING
        if default is attr.NOTHING and _is_optional_type(param.annotation):
            default = None
        final = param.kind is Parameter.KEYWORD_ONLY
        greedy = isinstance(annotation, type(Greedy))
        if greedy:
            annotation = annotation.converter
        accepts = cls.infer_accepts(annotation)
        argument = Argument(key, param.annotation, accepts, greedy, final, default=default)
        return argument

    @classmethod
    def infer_accepts(cls, annotation: _Annotation) -> QuantifiedNP:
        if _is_type_union(annotation):
            return cls.infer_union_type(annotation)
        conv = _get_type_converter(annotation)
        if conv:
            return cls.infer_accepts(conv(annotation))
        defined = _get_description(annotation)
        if defined:
            return defined
        if not isinstance(annotation, type):
            annotation = type(annotation)
        return QuantifiedNP(camel_case_to_spaces(annotation.__name__))

    @classmethod
    def infer_union_type(cls, annotation) -> QuantifiedNP:
        defined = _get_description(annotation)
        if defined:
            return defined
        constituents = _get_constituents(annotation)
        if len(constituents) == 1:
            return cls.infer_accepts(constituents[0])
        return reduce(or_, [cls.infer_accepts(t) for t in constituents])


@attr.s(eq=True, hash=True)
class CommandSignature:
    arguments: tuple[Argument, ...] = attr.ib(converter=lambda args: tuple(sorted(args)))
    description: str = attr.ib(default='', hash=False)

    def as_synopsis(self) -> str:
        return ' '.join(filter(None, (str(arg) for arg in self.arguments)))

    def as_node(self) -> str:
        return ' '.join(filter(None, (arg.as_node() for arg in self.arguments)))

    def as_frozenset(self) -> tuple[str, ...]:
        return frozenset(arg.key for arg in self.arguments if not arg.is_hidden)


@attr.s(kw_only=True)
class Documentation:
    name: str = attr.ib()
    parent: str = attr.ib()

    call_sign: str = attr.ib()
    description: str = attr.ib(default='(no description)')
    synopsis: tuple[str, ...] = attr.ib(converter=tuple, default=('(no synopsis)',))

    examples: dict[tuple[str, ...], str] = attr.ib(factory=dict)
    discussions: dict[str, str] = attr.ib(factory=dict)

    invocations: OrderedDict[frozenset[str], CommandSignature] = attr.ib(default=None)
    arguments: OrderedDict[str, Argument] = attr.ib(factory=OrderedDict, converter=OrderedDict)
    subcommands: dict[str, Documentation] = attr.ib(factory=dict)
    restrictions: list[str] = attr.ib(factory=list)

    hidden: bool = attr.ib(default=False)
    standalone: bool = attr.ib(default=False)
    aliases: list[str] = attr.ib(factory=list)
    invalid_syntaxes: set[frozenset[str]] = attr.ib(factory=set)

    sections: dict[str, str] = attr.ib(factory=dict)
    frozen: bool = attr.ib(default=False)

    text_helps: dict[str, str] = attr.ib(factory=dict)
    rich_helps: dict[str, Embed2] = attr.ib(factory=dict)

    @classmethod
    def from_command(cls, cmd: Command) -> Documentation:
        doc = cls(name=cmd.name, parent=cmd.full_parent_name,
                  call_sign=cmd.qualified_name,
                  standalone=getattr(cmd, 'invoke_without_command', True),
                  aliases=cmd.aliases)
        doc.infer_arguments(cmd.params)
        memo = cls.retrieve_memo(cmd)
        for f in reversed(memo):
            f(doc, cmd)
        return doc

    @classmethod
    def retrieve_memo(cls, cmd: Command) -> list[Callable[[Command], Command]]:
        memo = getattr(cmd, '__command_doc__', [])
        if not memo:
            memo = getattr(cmd._callback, '__command_doc__', [])
        return memo

    def iter_call_styles(self, options: deque[Argument] = None, stack: list[Argument] = None):
        if options is None:
            options = deque(self.arguments.values())
        if stack is None:
            stack = []
        if not options:
            yield CommandSignature(stack)
            return
        if options[0].is_unused:
            arg = options.popleft()
            yield from self.iter_call_styles(options, stack)
            options.appendleft(arg)
        elif options[0].is_optional or options[0].greedy:
            arg = options.popleft()
            yield from self.iter_call_styles(options, stack)
            stack.append(arg)
            yield from self.iter_call_styles(options, stack)
            options.appendleft(stack.pop())
        else:
            stack.append(options.popleft())
            yield from self.iter_call_styles(options, stack)
            options.appendleft(stack.pop())

    def format_examples(self, examples: list[tuple[str, Optional[str]]], transform=strong) -> str:
        if not examples:
            return '(none)'
        lines = []
        for invocation, explanation in examples:
            if isinstance(invocation, tuple):
                invocation = '\n'.join(invocation)
            lines.append(transform(escape_markdown(invocation)))
            if explanation:
                lines.append(blockquote(explanation))
        return '\n'.join(lines)

    def infer_arguments(self, args: dict[str, Parameter]):
        # Cannot use ismethod
        # Always skip the first argument which is either self/cls or context
        # If it is self/cls, ignore subsequent ones
        # that are annotated as Context
        arguments = OrderedDict()
        for k, v in [*args.items()][1:]:
            if (isinstance(v.annotation, type)
                    and issubclass(v.annotation, Context)):
                continue
            arguments[k] = Argument.from_parameter(v)
        arguments['__command__'] = Argument(
            key='__command__', annotation=None,
            accepts=None, greedy=False, final=False,
            default=None, help='', description='',
            node=self.call_sign, signature=self.call_sign,
            order=-1,
        )
        self.arguments = arguments

    def build_signatures(self):
        signatures = OrderedDict()
        for sig in self.iter_call_styles():
            signatures[sig.as_frozenset()] = sig
        return signatures

    def build_synopsis(self):
        lines = []
        for keys, sig in self.invocations.items():
            if keys not in self.invalid_syntaxes:
                lines.append(sig.as_synopsis())
        for subc in self.subcommands:
            lines.append(f'{subc} [...]')
        return tuple(lines)

    def ensure_signatures(self):
        if self.invocations is None:
            self.invocations = self.build_signatures()

    def add_subcommand(self, command: Command, doc: Documentation):
        self.subcommands[command.qualified_name] = doc

    def add_restriction(self, wrapper: CheckWrapper, *args, **kwargs):
        processor = CHECK_TRANSLATOR.get(wrapper)
        if processor:
            self.restrictions.extend(processor(*args, **kwargs))

    def finalize(self):
        if self.frozen:
            return
        self.frozen = True
        self.ensure_signatures()
        self.synopsis = self.build_synopsis()

        sections = self.sections
        sections['Synopsis'] = pre('\n'.join(self.synopsis))
        sections['Description'] = self.description

        invocations = {sig.as_node().strip(): sig.description
                       for keys, sig in self.invocations.items()
                       if keys not in self.invalid_syntaxes}
        subcommands = {f'{k} ...': f'{v.description} (subcommand)'
                       for k, v in self.subcommands.items()}

        sections['Syntax'] = self.format_examples(
            {**invocations, **subcommands}.items(),
            transform=lambda s: a('https://.', strong(s)),
        )
        arguments = [f'{strong(arg.key)}: {arg.describe()}'
                     for arg in self.arguments.values()
                     if not arg.is_hidden]
        sections['Arguments'] = '\n'.join(arguments)

        if self.restrictions:
            sections['Restrictions'] = '\n'.join(self.restrictions)
        if self.examples:
            sections['Examples'] = self.format_examples(self.examples.items())
        if self.discussions:
            sections['Discussions'] = self.format_examples(self.discussions.items())
        if self.aliases:
            sections['Aliases'] = ', '.join(self.aliases)

        self.assert_documentations()

        for s in self.HELP_STYLES:
            self.rich_helps[s], self.text_helps[s] = self.generate_help(s)

    def assert_documentations(self):
        sections = self.sections
        if sections['Description'] == '(no description)':
            log.warning(MissingDescription(self.call_sign))

    def generate_help(self, style: str) -> tuple[Embed2, str]:
        title, chapters = self.HELP_STYLES[style]
        sections = [(k, self.sections.get(k)) for k in chapters]
        sections = [(k, v) for k, v in sections if v]
        kwargs = {
            'sections': sections,
            'title': f'{title}: {self.call_sign}',
            'description': self.description,
        }
        rich_help = page_embed2(**kwargs)
        text_help = page_plaintext(**kwargs)
        return rich_help, text_help

    def format_argument_highlight(self, args: list, kwargs: dict, color='white') -> tuple[str, Argument]:
        args: deque = deque(args)
        kwargs: deque = deque(kwargs.items())
        arguments: deque = deque([*split_at(sorted(self.arguments.items(), key=lambda t: t[1]), lambda t: t[1].is_hidden)][-1])
        stack: list[str] = []
        while args:
            if isinstance(args.popleft(), (Context, Cog)):
                continue
            key, arg = arguments.popleft()
            stack.append(str(arg))
        while kwargs:
            kwargs.popleft()
            key, arg = arguments.popleft()
            stack.append(str(arg))
        if arguments:
            key, arg = arguments.popleft()
            stack.append(mta_arrow_bracket(strong(arg), color))
        if arguments:
            stack.append('...')
        return ' '.join(stack), arg

    HELP_STYLES = {
        'normal': ('Command', ['Syntax', 'Examples', 'Aliases']),
        'syntax': ('Syntax', ['Syntax']),
        'short': ('Help', ['Synopsis', 'Aliases']),
        'full': ('Documentation', ['Synopsis', 'Aliases', 'Syntax', 'Arguments', 'Examples', 'Restrictions', 'Discussions']),
        'examples': ('Examples', ['Examples']),
        'signature': ('Type signatures', ['Synopsis', 'Syntax', 'Arguments']),
    }