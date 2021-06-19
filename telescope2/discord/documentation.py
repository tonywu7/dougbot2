# doc.py
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
# command.py
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
from collections import defaultdict, deque
from fractions import Fraction
from functools import cached_property, partial, reduce
from inspect import Parameter
from operator import or_
from typing import (
    Any, Callable, Deque, Dict, List, Literal, Optional, Protocol, Tuple, Type,
    Union,
)

import attr
import discord
from discord import Embed, Forbidden
from discord.ext import commands
from discord.ext.commands import Command, Converter, Greedy
from discord.utils import escape_markdown
from django.utils.text import camel_case_to_spaces
from fuzzywuzzy import process as fuzzy
from more_itertools import partition

from telescope2.utils.datetime import utcnow
from telescope2.utils.functional import deferred
from telescope2.utils.lang import (
    QuantifiedNP, coord_conj, pluralize, singularize, slugify,
)

from .command import DocumentationMixin, Instruction, instruction, NoSuchCommand
from .context import Circumstances
from .converters import CaseInsensitive, Choice
from .utils.textutil import (
    blockquote, code, page_embed, page_plaintext, pre, strong,
)

_ALL_CHANNEL_TYPES = Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel]
_ALL_CHANNEL_TYPES_OPTIONAL = Union[discord.TextChannel, discord.VoiceChannel, discord.StageChannel, None]
_TEXT_AND_VC_TYPES = Union[discord.TextChannel, discord.VoiceChannel]
_TEXT_AND_VC_TYPES_OPTIONAL = Union[discord.TextChannel, discord.VoiceChannel, None]

TYPE_DESCRIPTIONS: Dict[Type, QuantifiedNP] = {
    int: QuantifiedNP('whole number'),
    float: QuantifiedNP('number', attributive='whole or decimal'),
    Fraction: QuantifiedNP('number', attributive='whole, decimal, or fractional'),

    str: QuantifiedNP('text'),
    bool: QuantifiedNP('yes', 'no', concise='yes/no'),

    discord.Member: QuantifiedNP('id', 'name', 'mention', concise='user', attributive="Discord user's"),
    discord.Role: QuantifiedNP('id', 'name', 'mention', concise='role', attributive="role's"),
    discord.TextChannel: QuantifiedNP('id', 'name', concise='text channel', attributive="text channel's"),
    discord.VoiceChannel: QuantifiedNP('id', 'name', concise='voice channel', attributive="voice channel's"),
    discord.Colour: QuantifiedNP('color', predicative=f'in hexadecimal {code("#fd7d1c")} or RGB {code("rgb(253,125,28)")}'),
    discord.Emoji: QuantifiedNP('emote', predicative='must be in servers the bot is in'),
    discord.PartialEmoji: QuantifiedNP('emote'),

    _ALL_CHANNEL_TYPES: QuantifiedNP('channel id', 'name', concise='channel', attributive="channel's"),
    _ALL_CHANNEL_TYPES_OPTIONAL: QuantifiedNP('channel id', 'name', concise='channel', attributive="channel's"),
    _TEXT_AND_VC_TYPES: QuantifiedNP('channel id', 'name', concise='channel', attributive="channel's"),
    _TEXT_AND_VC_TYPES_OPTIONAL: QuantifiedNP('channel id', 'name', concise='channel', attributive="channel's"),
}

_Converter = Union[Converter, Type[Converter]]

CheckPredicate = Callable[[Circumstances], bool]
CheckWrapper = Callable[[Command], Command]
CheckDecorator = Callable[..., CheckWrapper]

log = logging.getLogger('discord.commands')


class DescribedConverter(Protocol):
    __accept__: QuantifiedNP


class DescribedCheck(Protocol):
    description: List[str]


def _record_perm_check(place: str, **perms: bool) -> List[str]:
    denied, allowed = partition(lambda t: t[1], perms.items())
    denied = [strong(s) for s, v in denied]
    allowed = [strong(s) for s, v in allowed]
    msg = []
    if allowed:
        msg.append(f'Requires {coord_conj(*allowed)} perms in {place}')
    if denied:
        msg.append(f'Denies anyone with {coord_conj(*denied)} perms in {place}')
    return msg


def _record_owner_check():
    return ["Only the bot's owner can use this command."]


_record_server_perm_check = partial(_record_perm_check, 'server')
_record_channel_perm_check = partial(_record_perm_check, 'channel')

CHECK_TRANSLATOR: Dict[CheckDecorator, Callable[..., List[str]]] = {
    commands.has_permissions: _record_channel_perm_check,
    commands.has_guild_permissions: _record_server_perm_check,
    commands.is_owner: _record_owner_check,
}


def _is_type_union(annotation) -> bool:
    try:
        return annotation.__origin__ is Union
    except AttributeError:
        return False


def _is_optional_type(annotation) -> bool:
    try:
        return None in annotation.__args__
    except AttributeError:
        return False


def _is_converter(annotation: _Converter) -> bool:
    if isinstance(annotation, Converter):
        return True
    try:
        return issubclass(annotation, Converter)
    except TypeError:
        return False


def _constituent_types(annotation) -> Tuple[Type, ...]:
    try:
        return annotation.__args__
    except AttributeError:
        return ()


@attr.s(eq=True, hash=True)
class Argument:
    key: str = attr.ib()
    annotation: Type | _Converter = attr.ib()
    accepts: QuantifiedNP = attr.ib()
    greedy: bool = attr.ib()
    final: bool = attr.ib()
    default: Any = attr.ib(default=attr.NOTHING)
    help: str = attr.ib(default='')

    @property
    def is_unused(self) -> bool:
        return self.final and self.is_optional and not self.help

    @property
    def is_optional(self) -> bool:
        return self.default is not attr.NOTHING

    @cached_property
    def slug(self) -> str:
        return slugify(singularize(self.key))

    def describe(self) -> str:
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
            accepts = f'{accepts[:1].upper()}{accepts[1:]}'
        return accepts

    def as_signature(self) -> str:
        if self.is_unused:
            return ''
        if self.final:
            return f'[{self.accepts.concise(2)} ...]'
        if self.greedy:
            return f'[one or more {self.accepts.concise(2)}]'
        return f'[{self.accepts.concise(1)}]'

    def __str__(self):
        if self.is_unused:
            return '[...]'
        if self.final:
            return f'[{self.slug} ...]'
        if self.greedy:
            return f'{self.slug} [{self.slug} ...]'
        if self.is_optional:
            return f'[{self.slug}]'
        return f'<{self.slug}>'

    def __repr__(self):
        return self.slug

    @classmethod
    def from_parameter(cls, param: Parameter) -> Argument:
        key = param.name
        annotation = param.annotation
        if annotation is Parameter.empty:
            raise BadDocumentation(f'Parameter {param.name} is not annotated')
        default = param.default if param.default is not Parameter.empty else attr.NOTHING
        final = param.kind is Parameter.KEYWORD_ONLY
        greedy = isinstance(annotation, type(Greedy))
        if greedy:
            annotation = annotation.converter
        accepts = cls.infer_accepts(annotation)
        argument = Argument(key, param.annotation, accepts, greedy, final, default=default)
        return argument

    @classmethod
    def infer_accepts(cls, annotation: Type | DescribedConverter) -> QuantifiedNP:
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
        constituents = [*filter(lambda t: t is not type(None), _constituent_types(annotation))]  # noqa: E721
        if len(constituents) == 1:
            return cls.infer_accepts(constituents[0])
        return reduce(or_, [cls.infer_accepts(t) for t in constituents])


@attr.s(eq=True, hash=True)
class CommandSignature:
    arguments: Tuple[Argument, ...] = attr.ib(converter=tuple)
    description: str = attr.ib(default='', hash=False)

    def as_synopsis(self) -> str:
        return ' '.join(filter(None, (str(arg) for arg in self.arguments)))

    def as_signature(self) -> str:
        return ' '.join(filter(None, (arg.as_signature() for arg in self.arguments)))

    def as_tuple(self) -> Tuple[str, ...]:
        return tuple(arg.key for arg in self.arguments)


@attr.s(kw_only=True)
class Documentation:
    call_sign: str = attr.ib()
    description: str = attr.ib(default='(no description)')
    synopsis: Tuple[str, ...] = attr.ib(converter=tuple, default=('(no synopsis)',))

    examples: Dict[str, str] = attr.ib(factory=dict)
    discussions: Dict[str, str] = attr.ib(factory=dict)

    invocations: Dict[Tuple[str, ...], CommandSignature] = attr.ib(default=None)
    arguments: Dict[str, Argument] = attr.ib(factory=dict)
    subcommands: Dict[str, Documentation] = attr.ib(factory=dict)
    restrictions: List[str] = attr.ib(factory=list)
    hidden: bool = attr.ib(default=False)

    sections: Dict[str, str] = attr.ib(factory=dict)

    @classmethod
    def from_command(cls, cmd: Instruction) -> Documentation:
        doc = cls(call_sign=cmd.qualified_name)
        doc.arguments = doc.infer_arguments(cmd.params)
        return doc

    def iter_call_styles(self, options: Deque[Argument] = None, stack: List[Argument] = None):
        if options is None:
            options = deque(self.arguments.values())
        if stack is None:
            stack = []
        if not options:
            yield CommandSignature(stack)
            return
        arg = options.popleft()
        if arg.is_unused:
            yield from self.iter_call_styles(options, stack)
            options.append(arg)
        elif arg.is_optional or arg.greedy:
            yield from self.iter_call_styles(options, stack)
            stack.append(arg)
            yield from self.iter_call_styles(options, stack)
            options.append(stack.pop())
        else:
            stack.append(arg)
            yield from self.iter_call_styles(options, stack)
            options.appendleft(stack.pop())

    def format_examples(self, examples: List[Tuple[str, Optional[str]]], transform=strong) -> str:
        if not examples:
            return '(none)'
        lines = []
        for invocation, explanation in examples:
            lines.append(transform(escape_markdown(invocation)))
            if explanation:
                lines.append(blockquote(explanation))
        return '\n'.join(lines)

    def infer_arguments(self, args: Dict[str, Parameter]):
        # Cannot use ismethod
        # Always skip the first argument which is either self/cls or context
        # If it is self/cls, ignore subsequent ones
        # that are annotated as Context
        arguments = {}
        for k, v in [*args.items()][1:]:
            if v.annotation is Circumstances:
                continue
            arguments[k] = Argument.from_parameter(v)
        return arguments

    def build_signatures(self):
        signatures = {}
        for sig in self.iter_call_styles():
            signatures[sig.as_tuple()] = sig
        return signatures

    def build_synopsis(self):
        lines = []
        for sig in self.invocations.values():
            lines.append(f'{self.call_sign} {sig.as_synopsis()}')
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
        self.ensure_signatures()
        self.synopsis = self.build_synopsis()

        sections = self.sections
        sections['Synopsis'] = pre('\n'.join(self.synopsis))
        sections['Description'] = self.description

        invocations = {f'{self.call_sign} {sig.as_signature()}'.strip(): sig.description
                       for sig in self.invocations.values()}
        subcommands = {f'{k} ...': f'{v.description} (subcommand)'
                       for k, v in self.subcommands.items()}
        sections['Syntax'] = self.format_examples({**invocations, **subcommands}.items())
        arguments = [f'{strong(arg.key)}: {arg.describe()}' for arg in self.arguments.values()]
        sections['Arguments'] = '\n'.join(arguments)

        if self.restrictions:
            sections['Restrictions'] = '\n'.join(self.restrictions)
        if self.examples:
            sections['Examples'] = self.format_examples(self.examples.items())
        if self.discussions:
            sections['Discussions'] = self.format_examples(self.discussions.items())

        self.assert_documentations()

    def assert_documentations(self):
        sections = self.sections
        if sections['Description'] == '(no description)':
            log.warning(MissingDescription(self.call_sign))
        # if 'Examples' not in sections:
        #     log.warning(MissingExamples(self.call_sign))

    def generate_help(self, style: str) -> Tuple[Embed, str]:
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

    HELP_STYLES = {
        'normal': ('Command', ['Syntax', 'Examples', 'Restrictions']),
        'short': ('Help', ['Synopsis']),
        'full': ('Documentation', ['Synopsis', 'Syntax', 'Arguments', 'Examples', 'Restrictions', 'Discussions']),
        'examples': ('Examples', ['Examples']),
        'signature': ('Type signatures', ['Synopsis', 'Syntax', 'Arguments']),
    }
    HelpFormat = Choice(*sorted(HELP_STYLES.keys()), concise_name='info category')


@attr.s
class Manual:
    commands: Dict[str, Documentation] = attr.ib(factory=dict)
    sections: Dict[str, List[str]] = attr.ib(factory=lambda: defaultdict(list))

    toc: Dict[str, str] = attr.ib(factory=dict)
    toc_embed: Embed = attr.ib(default=None)
    toc_text: str = attr.ib(default=None)

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

    def finalize(self):
        for doc in self.commands.values():
            doc.finalize()
        for section, calls in sorted(self.sections.items(), key=lambda t: t[0]):
            lines = []
            for call in sorted(calls):
                command = self.commands[call]
                if command.hidden:
                    continue
                lines.append(f'{strong(call)}: {command.description}')
            self.toc[section] = '\n'.join(lines)
        self.toc_embed = page_embed(self.toc.items(), title='Command list')
        self.toc_text = page_plaintext(self.toc.items(), title='Command list')

    def lookup(self, query: str) -> Documentation:
        try:
            return self.commands[query]
        except KeyError:
            match = fuzzy.extractOne(query, self.commands.keys(), score_cutoff=65)
            if match:
                match = match[0]
            raise NoSuchCommand(query, match)


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
def argument(arg: str, desc: str, term: Optional[str | QuantifiedNP] = None):
    def wrapper(f: Instruction):
        argument = f.doc.arguments[arg]
        argument.help = desc
        if isinstance(term, QuantifiedNP):
            argument.accepts = term
        elif isinstance(term, str):
            argument.accepts = QuantifiedNP(term)
        return f
    return wrapper


@deferred(1)
def invocation(signature: Tuple[str], desc: str | Literal[False]):
    def wrapper(f: Instruction):
        f.doc.ensure_signatures()
        if desc:
            f.doc.invocations[signature].description = desc
        else:
            del f.doc.invocations[signature]
        return f
    return wrapper


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


@deferred(1)
def hidden():
    def wrapper(f: Instruction):
        f.doc.hidden = True
        return f
    return wrapper


@deferred(1)
def cooldown(rate: int, per: float, bucket: commands.BucketType | Callable[[discord.Message], Any]):
    def wrapper(f: Instruction):
        commands.cooldown(rate, per, bucket)(f)
        bucket_type = {
            commands.BucketType.default: 'globally',
            commands.BucketType.user: 'for each user',
            commands.BucketType.member: 'for each user',
            commands.BucketType.guild: 'for each server',
            commands.BucketType.channel: 'for each channel',
            commands.BucketType.category: 'for each channel category',
            commands.BucketType.role: 'for each role',
        }.get(bucket)
        cooldown = (f'Rate limited: {rate} {pluralize(rate, "call")} '
                    f'every {per} {pluralize(per, "second")}')
        if bucket_type is None:
            info = f'{cooldown}; dynamic.'
        else:
            info = f'{cooldown} {bucket_type}'
        f.doc.restrictions.append(info)
        return f
    return wrapper


async def _send_with_text_fallback(ctx: Circumstances, embed: Embed, text: str, **kwargs):
    try:
        return await ctx.reply_with_delete(embed=embed, **kwargs)
    except Forbidden:
        return await ctx.reply_with_delete(content=text, **kwargs)


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
        return await _send_with_text_fallback(ctx, toc_embed, toc_text)

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
    return await _send_with_text_fallback(ctx, rich_help, text_help)


class BadDocumentation(UserWarning):
    def __str__(self) -> str:
        return f'Bad documentation: {self.message}'


class MissingDescription(BadDocumentation):
    def __init__(self, call_sign: str) -> None:
        self.message = f'{call_sign}: No description provided'


class MissingExamples(BadDocumentation):
    def __init__(self, call_sign: str) -> None:
        self.message = f'{call_sign}: No command example provided'


__all__ = [
    'Documentation',
    'Manual',
    'discussion',
    'description',
    'argument',
    'invocation',
    'example',
]
