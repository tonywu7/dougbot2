# environment.py
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
from functools import cached_property, reduce, total_ordering
from inspect import Parameter
from itertools import chain
from operator import or_
from typing import (Callable, Literal, Optional, TypedDict, Union, get_args,
                    get_origin)

from discord.ext.commands import Bot, Cog, Command, Context, Converter, Greedy
from discord.utils import escape_markdown
from more_itertools import split_at

from ...utils.datastructures import TypeDictionary
from ...utils.english import QuantifiedNP, singularize, slugify
from ...utils.functional import get_memo
from ...utils.markdown import a, blockquote, em, pre, strong
from .exceptions import BadDocumentation, MissingDescription, NoSuchCommand

_Type = Union[type, Converter, type[Converter], Callable]
_TypeHint = Union[str, QuantifiedNP]
_TypePrinter = Union[_TypeHint, Callable[['Environment', _Type], Union[_Type, _TypeHint]]]

CheckPredicate = Callable[[Context], bool]
CheckWrapper = Callable[[Command], Command]
CheckDecorator = Callable[..., CheckWrapper]

_NOTHING = object()


class _EmbedField(TypedDict):
    name: str
    value: str
    inline: bool


class _Embed(TypedDict):
    title: str
    description: str
    fields: list[_EmbedField]


@total_ordering
class Argument:
    """Represent an argument for a command.

    Argument objects keep track of the argument's name, expected types,
    default values, and displayed names in command help.

    Argument objects are populated by the Documentation class when
    it inspects a command's function signature.
    """

    def __init__(self, env: Environment, param: Parameter) -> Argument:
        """Create an Argument description from an `inspect.Parameter` object."""

        annotation = param.annotation
        if annotation is Parameter.empty:
            raise BadDocumentation(f'Parameter {param.name} is not annotated')

        self.env = env
        self.key = param.name

        self.accepts = self.infer_accepts(annotation)

        self.greedy = isinstance(annotation, type(Greedy))
        self.final = param.kind is Parameter.KEYWORD_ONLY

        if param.default is not Parameter.empty:
            self.default = param.default
        elif self._is_optional_type(param.annotation):
            self.default = None
        else:
            self.default = _NOTHING

        if self.greedy:
            self.annotation = annotation.converter
        else:
            self.annotation = annotation

        self.help: str = ''
        self.description: str = ''
        self.node: str = ''
        self.signature: str = ''

        self.order: int = 0
        self.hidden: bool = False

    @property
    def is_hidden(self) -> str:
        """Whether this argument is marked as hidden or is private.

        Hidden arguments are not shown in the help page.
        """
        return self.hidden or self.key[0] == '_'

    @property
    def is_unused(self) -> bool:
        """Whether this argument is a "rest value" argument and\
        is expected to not be used.

        In discord.py, this is usually the first keyword-only argument.
        The argument is expected to not be used if it doesn't have an
        annotation or if the annotation is `str`.
        """
        return (self.final and self.is_optional
                and not self.help
                and not self.description)

    @property
    def is_optional(self) -> bool:
        """Whether this argument has a default value."""
        return self.default is not _NOTHING

    @cached_property
    def slug(self) -> str:
        """Return a kebab-case version of the argument name."""
        return slugify(singularize(self.key))

    @classmethod
    def _is_type_union(cls, annotation) -> bool:
        return get_origin(annotation) is Union  # type: ignore

    @classmethod
    def _is_literal_type(cls, annotation) -> bool:
        return get_origin(annotation) is Literal

    @classmethod
    def _is_optional_type(cls, annotation) -> bool:
        return type(None) in get_args(annotation)

    @classmethod
    def _get_constituents(cls, annotation) -> list[_Type]:
        constituents = filter(lambda t: t is not type(None), get_args(annotation))  # noqa: E721
        return [*split_at(constituents, cls._is_literal_type)][0]

    def describe(self) -> str:
        """Describe what this argument does and what it takes in the Argument secion."""
        if self.description:
            return self.description
        if self.is_unused:
            return '(Not used)'
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
            accepts = f'{self.help} Accept {accepts}'
        else:
            accepts = f'Accept {accepts}'
        return accepts

    def as_node(self) -> str:
        """Print this argument saying what type of info it accepts.

        This is used to format the list of possible ways to use a command,
        for example:

            message [channel] [content]

        """
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
        """Print the argument's name in manpage style.

        This is used to show the command signature in the synopsis.
        """
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

    def __lt__(self, other: Argument):
        if not isinstance(other, Argument):
            return NotImplemented
        return self.order - other.order

    def _to_comparable(self):
        return (type(self), self.key, self.annotation, self.default,
                self.greedy, self.final, self.order)

    def __eq__(self, other):
        if not isinstance(other, Argument):
            return NotImplemented
        return self._to_comparable() == other._to_comparable()

    def __hash__(self):
        return hash(self._to_comparable())

    def infer_accepts(self, annotation: _Type) -> QuantifiedNP:
        """Create a phrase in natural English describing the type of info this argument expects."""
        if self._is_type_union(annotation):
            return self.infer_union_type(annotation)
        if printer := self.env.types.get(annotation):
            if callable(printer):
                printer = printer(self.env, annotation)
            if not isinstance(printer, QuantifiedNP):
                return self.infer_accepts(printer)
            return printer
        self.env.log.warning(f'No type description for {annotation}')
        return QuantifiedNP(annotation.__name__)

    def infer_union_type(self, annotation) -> QuantifiedNP:
        """Handle Union types while describing the argument's type."""
        if printer := self.env.types.get(annotation):
            if callable(printer):
                return printer(self.env, annotation)
            return printer
        constituents = self._get_constituents(annotation)
        if len(constituents) == 1:
            return self.infer_accepts(constituents[0])
        return reduce(or_, [self.infer_accepts(t) for t in constituents])


class CommandSignature:
    """An ordered of Arguments representing one possible way to call a command.

    This object is used to format command synopsis and syntax help.
    """

    def __init__(self, arguments: tuple[Argument, ...], description: str):
        self.arguments = tuple(sorted(arguments))
        self.description = description

    def as_synopsis(self) -> str:
        """Print a manpage style signature.

        For example, with a command whose function signature is

            `message(channel: Channel, *, content: Optional[str] = None)`

        This prints

            `message ‹channel› [content]`

        """
        return ' '.join(filter(None, (str(arg) for arg in self.arguments)))

    def as_node(self) -> str:
        """Print the signature indicating the types of each argument.

        For example, with a command whose function signature is

            `message(channel: Channel, *, content: Optional[str] = None)`

        This prints

            `message [text channel] [text content ...]`

        """
        return ' '.join(filter(None, (arg.as_node() for arg in self.arguments)))

    def as_frozenset(self) -> tuple[str, ...]:
        """Return the names of these arguments as a frozenset (thus ignoring the order).

        This is useful as dict keys in mappings of command signatures.
        """
        return frozenset(arg.key for arg in self.arguments if not arg.is_hidden)

    def __eq__(self, other):
        if not isinstance(other, CommandSignature):
            return NotImplemented
        return self.arguments == other.arguments

    def __hash__(self):
        return hash((type(self), self.arguments))


class Documentation:
    """Documentation objects contain all information necessary\
    to produce a detailed help page for a command.

    The autodoc module instantiates one Documentation object from one
    discord.py Command object, reading its function signature and generating
    descriptions.

    This relies on the Command callbacks being augmented with the provided decorators,
    which convey the command's description, call syntax, and usage examples, etc.

    See `autodoc.decorators` for more info.
    """

    def __init__(self, env: Environment, cmd: Command):
        self.env = env

        self.name: str = cmd.name
        self.parent: str = cmd.full_parent_name
        self.call_sign: str = cmd.qualified_name

        self.standalone: bool = getattr(cmd, 'invoke_without_command', True)
        self.aliases: list[str] = cmd.aliases

        self.description: str = '(no description)'
        self.synopsis: tuple[str, ...] = ('(no synopsis)',)
        self.examples: dict[tuple[str, ...], str] = {}
        self.discussions: dict[str, str] = {}

        self.invocations: OrderedDict[frozenset[str], CommandSignature] = OrderedDict()
        self.arguments: OrderedDict[str, Argument] = OrderedDict()
        self.subcommands: dict[str, Documentation] = {}
        self.restrictions: list[str] = []

        self.hidden: bool = False
        self.standalone: bool = False
        self.aliases: list[str] = []
        self.invalid_syntaxes: set[frozenset[str]] = set()

        self.sections: dict[str, str] = {}
        self.frozen: bool = False

        self.export: _Embed = {}

        self.infer_arguments(cmd.params)
        memo = get_memo(cmd, '__command_doc__', '_callback', default=[])
        for func in reversed(memo):
            func(self, cmd)

    @property
    def invisible(self):
        """Whether or not this command should be hidden from the table of contents.

        A command is visible if it is marked with the `autodoc.hidden` decorator
        or if it is a command group that cannot be called without subcommands
        (`invoke_without_command=False`).
        """
        return self.hidden or not self.standalone

    @property
    def full_aliases(self) -> list[str]:
        """All possible names for this command (including parent command).

        This is used to provide search results for a command if people look it up
        by its alias.
        """
        return [f'{self.parent} {alias}' for alias in self.aliases]

    def iter_call_styles(self, options: deque[Argument] = None, stack: list[Argument] = None):
        """Iterate over all possible call syntaxes for this command.

        Syntaxes are different if they take different sets of arguments.
        This happens when the command accepts optional arguments
        (thus where it runs without the optional argument and where it runs
        with the argument are two different call styles.

        For example, a command whose function signature is

            `message(channel: Channel, *, content: Optional[str] = None)`

        will have two call styles:

            `message channel`

            `message channel content`

        This helps clarify to people how the command may behave differently
        depending on how they call it.
        """
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

    def infer_arguments(self, args: dict[str, Parameter]):
        """Create Argument objects from a Parameter mapping."""
        # Cannot use ismethod
        # Always skip the first argument which is either self/cls or context
        # If it is self/cls, ignore subsequent ones
        # that are annotated as Context
        arguments = OrderedDict()
        for k, v in [*args.items()][1:]:
            if (isinstance(v.annotation, type)
                    and issubclass(v.annotation, Context)):
                continue
            if v.kind is Parameter.VAR_KEYWORD:
                continue
            arguments[k] = Argument(self.env, v)
        # arguments['__command__'] = Argument(
        #     key='__command__', annotation=None,
        #     accepts=None, greedy=False, final=False,
        #     default=None, help='', description='',
        #     node=self.call_sign, signature=self.call_sign,
        #     order=-1,
        # )
        self.arguments = arguments

    def build_signatures(self):
        """Create a mapping of all call signatures for this command."""
        signatures = OrderedDict()
        for sig in self.iter_call_styles():
            signatures[sig.as_frozenset()] = sig
        return signatures

    def build_synopsis(self):
        """Format the Synopsis section."""
        lines = []
        for keys, sig in self.invocations.items():
            if keys not in self.invalid_syntaxes:
                lines.append(sig.as_synopsis())
        for subc in self.subcommands:
            lines.append(f'{subc} [...]')
        return tuple(lines)

    def format_examples(
        self, examples: list[tuple[str, Optional[str]]],
        transform=lambda s: strong(escape_markdown(s)),
    ) -> str:
        """Format the Examples section of the help page."""
        if not examples:
            return '(none)'
        lines = []
        for invocation, explanation in examples:
            if isinstance(invocation, tuple):
                invocation = '\n'.join(invocation)
            lines.append(transform(invocation))
            if explanation:
                lines.append(blockquote(explanation))
        return '\n'.join(lines)

    def ensure_signatures(self):
        """Build function signatures if it has not been done."""
        if self.invocations is None:
            self.invocations = self.build_signatures()

    def add_subcommand(self, command: Command, doc: Documentation):
        """Add the documentation of this command's subcommand to the collection.

        Since there will only ever be one Documentation object for each Command
        object, all documentations will have a reference to those of their
        subcommands. This creates a tree structure.
        """
        self.subcommands[command.qualified_name] = doc

    def add_restriction(self, deco: CheckDecorator, desc: str, /, **kwargs):
        """Document a command check, cooldown, or concurrency limit.

        Natural language description will be generated for each restrictions.
        """
        if desc:
            self.restrictions.append(desc)
        else:
            if printer := self.env.types.get(deco, **kwargs):
                if callable(printer):
                    desc = printer(self.env, deco, **kwargs)
                else:
                    desc = printer
                self.restrictions.append(desc)
            elif deco.__doc__:
                self.restrictions.append(deco.__doc__)

    def finalize(self):
        """Generate all texts and produce the final embed object for this documentation."""
        if self.frozen:
            return
        self.frozen = True
        self.ensure_signatures()
        self.synopsis = self.build_synopsis()

        sections = self.sections
        sections['Synopsis'] = pre('\n'.join(self.synopsis))

        if self.aliases:
            sections['Shorthands'] = ', '.join(self.full_aliases)

        invocations = {sig.as_node().strip(): sig.description
                       for keys, sig in self.invocations.items()
                       if keys not in self.invalid_syntaxes}
        subcommands = {f'{k} ...': f'{v.description} (subcommand)'
                       for k, v in self.subcommands.items()}

        sections['Syntax'] = self.format_examples(
            {**invocations, **subcommands}.items(),
            transform=lambda s: a(strong(s), 'https://.'),
        )

        if self.restrictions:
            sections['Restrictions'] = '\n'.join(self.restrictions)
        if self.examples:
            examples = self.format_examples(
                self.examples.items(),
                lambda s: '\n' + strong(s),
            )
            sections['Examples'] = examples

        arguments = [f'{strong(arg.key)}: {arg.describe()}'
                     for arg in self.arguments.values()
                     if not arg.is_hidden and not arg.is_unused]
        sections['Arguments'] = '\n'.join(arguments)

        for k, v in self.discussions.items():
            sections[k] = v

        self.assert_documentations()
        self.export = self.generate_help()

    def assert_documentations(self):
        """Assert that documentations must contain some required information.

        Currently, this logs a warning if the command does not have a description.
        """
        if not self.description:
            self.env.log.warning(MissingDescription(self.call_sign))

    def generate_help(self) -> dict:
        """Format the help embed and return it as a dict."""
        sections = [{'name': k, 'value': v, 'inline': False} for k, v
                    in self.sections.items() if v]
        title = f'Help: {self.call_sign}'
        return {'title': title, 'description': self.description,
                'fields': sections}


class Manual:
    """A collection of command help pages.

    A fully-instantiated discord.py Bot instance creates a Manual by
    passing itself to the `from_bot` method. The Manual is then responsible
    for walking through all registered commands in the Bot, creating
    a Documentation object for each Command, and create a table of contents
    embed.

    The bot is responsible for creating its own help command and call
    appropriate functions on the Manual to generate help pages. This means
    the help command itself can also be augmented using this module.

    The Manual object does not keep track of command (de)registration
    after it has been finalized. If e.g. the Bot loads a new cog,
    it is responsible for creating an up-to-date Manual object.
    """

    def __init__(self, env: Environment, bot: Bot):
        self.env = env
        self.commands: dict[str, Documentation] = {}

        self.sections: dict[str, list[str]] = defaultdict(list)
        self.descriptions: dict[str, str] = defaultdict(str)
        self.aliases: dict[str, str] = {}

        self.toc: dict[str, str] = {}
        self.export: _Embed = {}
        self.frozen: bool = False

        sections: dict[tuple[int, str], list[str]] = defaultdict(list)
        descriptions = {}
        all_commands: dict[str, Command] = {cmd.qualified_name: cmd for cmd
                                            in bot.walk_commands()}

        for call, cmd in all_commands.items():
            self.commands[call] = Documentation(env, cmd)
            if cmd.cog and (sort_order := getattr(cmd.cog, 'sort_order', 0)):
                cog: Cog = cmd.cog
                section = (sort_order, cog.qualified_name)
                desc = cog.description
            else:
                section = (99, 'Miscellaneous')
                desc = ''
            sections[section].append(call)
            descriptions[section] = desc

        for call, cmd in all_commands.items():
            parent = self.commands[cmd.qualified_name]
            subcommands: list[Command] = getattr(cmd, 'commands', None) or []
            for subcmd in subcommands:
                subdoc = self.commands[subcmd.qualified_name]
                parent.add_subcommand(subcmd, subdoc)

        for (idx, k), calls in sorted(sections.items(), key=lambda t: t[0]):
            self.sections[k] = calls
            self.descriptions[k] = descriptions[idx, k]

    def propagate_restrictions(self, tree: dict[str, Documentation],
                               stack: list[list[str]],
                               seen: set[str]):
        """Include restrictions from parent commands in subcommands' help page."""
        for call_sign, doc in tree.items():
            if call_sign in seen:
                continue
            if doc.standalone:
                continue
            seen.add(call_sign)
            restrictions = [f'(Parent) {r}' for r in doc.restrictions]
            doc.restrictions.extend(chain.from_iterable(stack))
            stack.append(restrictions)
            self.propagate_restrictions(doc.subcommands, stack, seen)
            stack.pop()

    def register_aliases(self):
        """Create a mapping of all possible command names to support lookup by aliases."""
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
        """Generate all help pages and the table of content."""
        if self.frozen:
            return
        self.frozen = True
        self.propagate_restrictions(self.commands, [], set())
        self.register_aliases()
        for doc in self.commands.values():
            doc.finalize()
        for section, calls in self.sections.items():
            lines = []
            desc = self.descriptions[section]
            if desc:
                lines.append(em(desc))
            for call in sorted(calls):
                doc = self.commands[call]
                if doc.invisible:
                    continue
                lines.append(f'{strong(call)}: {doc.description}')
            content = '\n'.join(lines)
            if content.strip():
                self.toc[section] = blockquote(content)

        fields = [{'name': k, 'value': v, 'inline': False}
                  for k, v in self.toc.items()]
        self.export = {'fields': fields}

    def lookup(self, query: str, hidden=False) -> Documentation:
        """Look up a command by name and return its documentation.

        :param query: Query to look up
        :type query: str
        :param hidden: Whether to include hidden commands, defaults to False
        :type hidden: bool, optional
        :raises NoSuchCommand: If there are no match
        (or if the matched command is hidden)
        :rtype: Documentation
        """
        doc = self.commands.get(query)
        if not doc:
            aliased = self.aliases.get(query)
            doc = self.commands.get(aliased)
        if (not doc or not hidden and doc.invisible):
            try:
                # TODO: replace with rapidfuzz
                from fuzzywuzzy import process as fuzzy
                from fuzzywuzzy.fuzz import UQRatio
                matched = fuzzy.extractBests(query, self.commands.keys(),
                                             scorer=UQRatio,
                                             score_cutoff=65)
            except ModuleNotFoundError:
                matched = None
            else:
                if matched:
                    for cmd, weight in matched:
                        if cmd == query:
                            continue
                        if not hidden and self.commands[cmd].invisible:
                            continue
                        matched = cmd
                        break
                    else:
                        matched = None
            raise NoSuchCommand(query, matched)
        return doc


TypeDict = TypeDictionary[_Type, _TypePrinter]


class Environment:
    """Centralized object managing autodoc generation.

    Documentation and Manual objects have access to the Environment,
    and from which to type printers.
    """

    def __init__(self, types: Optional[TypeDict] = None):
        self.log = logging.getLogger('discord.autodoc')
        self.types: TypeDict = TypeDictionary(types)
        self.manual: Manual

    def merge(self, *envs: Environment):
        """Include all definitions from these environments in the\
        dictionary in this Environment."""
        for env in envs:
            self.types._dict.update(env.types._dict)

    def init_bot(self, bot: Bot):
        """Create a Manual for this Environment from an initialized bot."""
        self.manual = Manual(self, bot)
        self.manual.finalize()
