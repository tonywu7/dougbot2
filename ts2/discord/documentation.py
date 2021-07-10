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
from collections import OrderedDict, defaultdict, deque
from fractions import Fraction
from functools import cached_property, partial, reduce
from inspect import Parameter
from operator import or_
from typing import Any, Callable, Literal, Optional, Protocol, Union

import attr
import discord
from discord import Embed, MessageReference
from discord.ext import commands
from discord.ext.commands import Cog, Command, Converter, Greedy
from discord.ext.commands.errors import UserInputError
from discord.utils import escape_markdown
from django.utils.text import camel_case_to_spaces
from fuzzywuzzy import process as fuzzy
from more_itertools import flatten, partition, split_at

from ts2.utils.datetime import utcnow
from ts2.utils.functional import deferred
from ts2.utils.lang import (QuantifiedNP, pl_cat_predicative, pluralize,
                            singularize, slugify)

from .command import (DocumentationMixin, Instruction, NoSuchCommand,
                      instruction)
from .context import Circumstances
from .converters import CaseInsensitive, Choice, ReplyRequired
from .utils.markdown import (a, blockquote, code, mta_arrow_bracket,
                             page_embed, page_plaintext, pre, strong)

_AllChannelTypes = Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]
_TextAndVCs = Union[discord.TextChannel, discord.VoiceChannel]

TYPE_DESCRIPTIONS: dict[type, QuantifiedNP] = {
    int: QuantifiedNP('whole number'),
    float: QuantifiedNP('number', attributive='whole or decimal'),
    Fraction: QuantifiedNP('number', attributive='whole, decimal, or fractional'),

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

BUCKET_DESCRIPTIONS = {
    commands.BucketType.default: 'globally',
    commands.BucketType.user: 'for each user',
    commands.BucketType.member: 'for each user',
    commands.BucketType.guild: 'for each server',
    commands.BucketType.channel: 'for each channel',
    commands.BucketType.category: 'for each channel category',
    commands.BucketType.role: 'for each role',
}

_Converter = Union[Converter, type[Converter]]

CheckPredicate = Callable[[Circumstances], bool]
CheckWrapper = Callable[[Command], Command]
CheckDecorator = Callable[..., CheckWrapper]

log = logging.getLogger('discord.commands')


def infinidict():
    return defaultdict(infinidict)


def infinigetitem(d: defaultdict, key: tuple):
    for k in key:
        d = d[k]
    return d


def infinisetitem(d: defaultdict, key: tuple, value: Any):
    if not key:
        raise ValueError
    for k in key[:-1]:
        d = d[k]
    d[key[-1]] = value


def infinidelitem(d: defaultdict, key: tuple):
    if not key:
        raise ValueError
    for k in key[:-1]:
        d = d[k]
    del d[key[-1]]


class DescribedConverter(Protocol):
    __accept__: QuantifiedNP


class DescribedCheck(Protocol):
    description: list[str]


def describe_concurrency(number: int, bucket: commands.BucketType):
    bucket_type = BUCKET_DESCRIPTIONS[bucket]
    info = (f'maximum {number} {pluralize(number, "call")} '
            f'running at the same time {bucket_type}')
    return info


def readable_perm_name(p: str) -> str:
    return p.replace('_', ' ').replace('guild', 'server').title()


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
    try:
        return annotation.__origin__ is Union
    except AttributeError:
        return False


def _is_literal_type(annotation) -> bool:
    try:
        return annotation.__origin__ is Literal
    except AttributeError:
        return False


def _is_optional_type(annotation) -> bool:
    try:
        return type(None) in annotation.__args__
    except AttributeError:
        return False


def _is_converter(annotation: _Converter) -> bool:
    if isinstance(annotation, Converter):
        return True
    try:
        return issubclass(annotation, Converter)
    except TypeError:
        return False


def _constituent_types(annotation) -> tuple[type, ...]:
    try:
        return annotation.__args__
    except AttributeError:
        return ()


@attr.s(eq=True, hash=True)
class Argument:
    key: str = attr.ib(order=False)
    annotation: type | _Converter = attr.ib(order=False)
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
                accepts = f'{accepts}, defaults to {self.default}'
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
    def infer_accepts(cls, annotation: type | DescribedConverter) -> QuantifiedNP:
        if _is_type_union(annotation):
            return cls.infer_union_type(annotation)
        defined = TYPE_DESCRIPTIONS.get(annotation)
        if defined:
            return defined
        try:
            if isinstance(annotation.__accept__, QuantifiedNP):
                return annotation.__accept__
        except AttributeError:
            pass
        if not isinstance(annotation, type):
            annotation = type(annotation)
        return QuantifiedNP(camel_case_to_spaces(annotation.__name__))

    @classmethod
    def infer_union_type(cls, annotation) -> QuantifiedNP:
        defined = TYPE_DESCRIPTIONS.get(annotation)
        if defined:
            return defined
        constituents = filter(lambda t: t is not type(None), _constituent_types(annotation))  # noqa: E721
        constituents = [*split_at(constituents, _is_literal_type)][0]
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

    examples: dict[str, str] = attr.ib(factory=dict)
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

    @classmethod
    def from_command(cls, cmd: Instruction) -> Documentation:
        doc = cls(name=cmd.name, parent=cmd.full_parent_name,
                  call_sign=cmd.qualified_name,
                  standalone=getattr(cmd, 'invoke_without_command', True),
                  aliases=cmd.aliases)
        doc.infer_arguments(cmd.params)
        return doc

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
            if v.annotation is Circumstances:
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

    def add_subcommand(self, command: Instruction):
        self.subcommands[command.qualified_name] = command.doc

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

    def assert_documentations(self):
        sections = self.sections
        if sections['Description'] == '(no description)':
            log.warning(MissingDescription(self.call_sign))

    def generate_help(self, style: str) -> tuple[Embed, str]:
        title, chapters = self.HELP_STYLES[style]
        sections = [(k, self.sections.get(k)) for k in chapters]
        sections = [(k, v) for k, v in sections if v]
        kwargs = {
            'sections': sections,
            'title': f'{title}: {self.call_sign}',
            'description': self.description,
        }
        rich_help = page_embed(**kwargs)
        text_help = page_plaintext(**kwargs)
        return rich_help, text_help

    def format_argument_highlight(self, args: list, kwargs: dict, color='white') -> tuple[str, Argument]:
        args: deque = deque(args)
        kwargs: deque = deque(kwargs.items())
        arguments: deque = deque([*split_at(sorted(self.arguments.items(), key=lambda t: t[1]), lambda t: t[1].is_hidden)][-1])
        stack: list[str] = []
        while args:
            if isinstance(args.popleft(), (Circumstances, Cog)):
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
        'syntax': ('Help', ['Syntax']),
        'short': ('Help', ['Synopsis', 'Aliases']),
        'full': ('Documentation', ['Synopsis', 'Aliases', 'Syntax', 'Arguments', 'Examples', 'Restrictions', 'Discussions']),
        'examples': ('Examples', ['Examples']),
        'signature': ('Type signatures', ['Synopsis', 'Syntax', 'Arguments']),
    }
    HelpFormat = Choice[HELP_STYLES.keys(), 'info category']


@deferred(1)
def example(invocation: str, explanation: str):
    def wrapper(f: Instruction):
        f.doc.examples[f'{f.doc.call_sign} {invocation}'] = explanation
        return f
    return wrapper


@deferred(1)
def description(desc: str):
    def wrapper(f: Instruction):
        f.doc.description = desc
        return f
    return wrapper


@deferred(1)
def discussion(title: str, body: str):
    def wrapper(f: Instruction):
        f.doc.discussions[title] = body
        return f
    return wrapper


@deferred(1)
def argument(arg: str, help: str = '', *, node: str = '',
             signature: str = '', term: Optional[str | QuantifiedNP] = None):
    def wrapper(f: Instruction):
        argument = f.doc.arguments[arg]
        argument.help = help
        argument.node = node
        argument.signature = signature
        if isinstance(term, QuantifiedNP):
            argument.accepts = term
        elif isinstance(term, str):
            argument.accepts = QuantifiedNP(term)
        return f
    return wrapper


@deferred(1)
def invocation(signature: tuple[str, ...], desc: str | Literal[False]):
    signature: frozenset[str] = frozenset(signature)

    def wrapper(f: Instruction):
        f.doc.ensure_signatures()
        if desc:
            f.doc.invocations[signature].description = desc
            f.doc.invocations.move_to_end(signature, last=True)
            f.doc.invalid_syntaxes.discard(signature)
        else:
            if signature not in f.doc.invocations:
                raise KeyError(signature)
            f.doc.invalid_syntaxes.add(signature)
        return f
    return wrapper


@deferred
def use_syntax_whitelist(f: Instruction):
    f.doc.ensure_signatures()
    f.doc.invalid_syntaxes |= f.doc.invocations.keys()
    return f


@deferred(1)
def restriction(deco_func_or_desc: CheckDecorator | str, *args, **kwargs) -> CheckWrapper:
    def wrapper(f: Instruction):
        if callable(deco_func_or_desc):
            f.doc.add_restriction(deco_func_or_desc, *args, **kwargs)
            deco_func_or_desc(*args, **kwargs)(f)
        else:
            f.doc.restrictions.append(deco_func_or_desc)
        return f
    return wrapper


@deferred
def hidden(f: Instruction):
    f.doc.hidden = True
    return f


@deferred(1)
def cooldown(rate: int, per: float, bucket: commands.BucketType | Callable[[discord.Message], Any]):
    def wrapper(f: Instruction):
        commands.cooldown(rate, per, bucket)(f)
        bucket_type = BUCKET_DESCRIPTIONS.get(bucket)
        cooldown = (f'Rate limited: {rate} {pluralize(rate, "call")} '
                    f'every {per} {pluralize(per, "second")}')
        if bucket_type is None:
            info = f'{cooldown}; dynamic.'
        else:
            info = f'{cooldown} {bucket_type}'
        f.doc.restrictions.append(info)
        return f
    return wrapper


@deferred(1)
def concurrent(number: int, bucket: commands.BucketType, *, wait=False):
    def wrapper(f: Instruction):
        commands.max_concurrency(number, bucket, wait=wait)(f)
        f.doc.restrictions.append(describe_concurrency(number, bucket).capitalize())
        return f
    return wrapper


@deferred(1)
def accepts_reply(desc: str = 'Reply to a message', required=False):
    async def inject_reply(self_or_ctx: Cog | Circumstances, *args):
        if not isinstance(self_or_ctx, Circumstances):
            ctx = args[0]
        else:
            ctx = self_or_ctx
        reply: MessageReference = ctx.message.reference
        if reply is None and required:
            raise ReplyRequired()
        ctx.kwargs['reply'] = reply

    def wrapper(f: Instruction):
        f.before_invoke(inject_reply)
        arg = f.doc.arguments['reply']
        arg.description = desc
        arg.signature = '(with reply)'
        arg.node = '┌ (while replying to a message)\n'
        arg.order = -2
        return f
    return wrapper


@attr.s
class Manual:
    commands: dict[str, Documentation] = attr.ib(factory=dict)
    sections: dict[str, list[str]] = attr.ib(factory=lambda: defaultdict(list))
    aliases: dict[str, str] = attr.ib(factory=dict)

    toc: dict[str, str] = attr.ib(factory=dict)
    toc_embed: Embed = attr.ib(default=None)
    toc_text: str = attr.ib(default=None)

    frozen: bool = attr.ib(default=False)

    @classmethod
    def from_bot(cls, bot):
        man = Manual()
        for call, cmd in bot.iter_commands():
            call: str
            cmd: DocumentationMixin
            man.commands[call] = cmd.doc
            if cmd.cog:
                section = cmd.cog.qualified_name
            else:
                section = 'Miscellaneous'
            man.sections[section].append(call)
        return man

    def propagate_restrictions(self, tree: dict[str, Documentation],
                               stack: list[list[str]],
                               seen: set[str]):
        for call_sign, doc in tree.items():
            if call_sign in seen:
                continue
            seen.add(call_sign)
            restrictions = [f'(Parent) {r}' for r in doc.restrictions]
            doc.restrictions.extend(flatten(stack))
            stack.append(restrictions)
            self.propagate_restrictions(doc.subcommands, stack, seen)
            stack.pop()

    def register_aliases(self):
        aliases: dict[str, list[str]] = defaultdict(list)
        for call_sign, doc in self.commands.items():
            aliased_prefixes = [*aliases[doc.parent]]
            aliased_prefixes.append(doc.parent)
            for prefix in aliased_prefixes:
                for alias in [doc.name, *doc.aliases]:
                    aliases[call_sign].append(f'{prefix} {alias}'.strip())
        for call_sign, aliases_ in aliases.items():
            for alias in aliases_:
                self.aliases[alias] = call_sign

    def finalize(self):
        if self.frozen:
            return
        self.frozen = True
        self.propagate_restrictions(self.commands, [], set())
        self.register_aliases()
        for doc in self.commands.values():
            doc.finalize()
        for section, calls in sorted(self.sections.items(), key=lambda t: t[0]):
            lines = []
            for call in sorted(calls):
                doc = self.commands[call]
                if doc.hidden or not doc.standalone:
                    continue
                lines.append(f'{strong(call)}: {doc.description}')
            content = '\n'.join(lines)
            if content.strip():
                self.toc[section] = content
        self.toc_embed = page_embed(self.toc.items(), title='Command list')
        self.toc_text = page_plaintext(self.toc.items(), title='Command list')

    def lookup(self, query: str) -> Documentation:
        try:
            return self.commands[query]
        except KeyError:
            pass
        try:
            aliased = self.aliases[query]
            return self.commands[aliased]
        except KeyError:
            match = fuzzy.extractOne(query, self.commands.keys(), score_cutoff=65)
            if match:
                match = match[0]
            raise NoSuchCommand(query, match)

    def hidden_commands(self) -> dict[str, Documentation]:
        return {k: v for k, v in self.commands.items() if v.hidden}

    @instruction('help', aliases=['man', 'man:tty'])
    @description('Get help about commands.')
    @argument('category', 'What kind of help info to get.')
    @argument('query', 'A command name, such as "echo" or "prefix set".')
    @invocation((), 'See all commands.')
    @invocation(('query',), 'See help for a command.')
    @invocation(('category',), False)
    @invocation(('category', 'query'), 'See specific info about a command, such as argument types.')
    @example('perms', f'Check help doc for {code("perms")}')
    @example('full perms', f'See detailed information about the command {code("perms")}')
    @example('prefix set', f'Check help doc for {code("prefix set")}, where {code("set")} is a subcommand of {code("prefix")}')
    async def help_command(ctx: Circumstances,
                           category: Optional[Documentation.HelpFormat] = 'normal',
                           *, query: CaseInsensitive = ''):
        man = ctx.manual
        use_plaintext = ctx.invoked_with == 'man:tty'

        def set_embed_info(embed: Embed):
            embed.set_author(name=ctx.me.display_name, icon_url=ctx.me.avatar_url)
            embed.timestamp = utcnow()

        if not query:
            toc_embed = man.toc_embed.copy()
            set_embed_info(toc_embed)
            toc_embed.set_footer(text=f'Use "{ctx.prefix}{ctx.invoked_with} [command]" to see help info for that command')
            toc_text = man.toc_text
            if use_plaintext:
                return await ctx.send(toc_text)
            return await ctx.reply_with_text_fallback(toc_embed, toc_text)

        if query[:len(ctx.prefix)] == ctx.prefix:
            query = query[len(ctx.prefix):]

        try:
            doc = man.lookup(query)
        except NoSuchCommand as exc:
            return await ctx.send(str(exc), delete_after=60)

        rich_help, text_help = doc.generate_help(category)
        set_embed_info(rich_help)
        if category == 'normal':
            rich_help.set_footer(text=f'Use "{ctx.prefix}{ctx.invoked_with} full {query}" for more info')

        if use_plaintext:
            return await ctx.send(text_help)
        return await ctx.reply_with_text_fallback(rich_help, text_help)


class BadDocumentation(UserWarning):
    def __str__(self) -> str:
        return f'Bad documentation: {self.message}'


class MissingDescription(BadDocumentation):
    def __init__(self, call_sign: str) -> None:
        self.message = f'{call_sign}: No description provided'


class MissingExamples(BadDocumentation):
    def __init__(self, call_sign: str) -> None:
        self.message = f'{call_sign}: No command example provided'


class SendHelp(UserInputError):
    def __init__(self, category='normal', *args):
        self.category = category
        super().__init__(message=None, *args)


class NotAcceptable(UserInputError):
    def __init__(self, message, *args):
        super().__init__(message=message, *args)