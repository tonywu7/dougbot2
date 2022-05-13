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
from typing import (
    Callable,
    Literal,
    Optional,
    Protocol,
    TypedDict,
    Union,
    get_args,
    get_origin,
    runtime_checkable,
)

from discord.ext.commands import Bot, Cog, Command, Context, Greedy
from discord.utils import escape_markdown
from more_itertools import split_at

from ...blueprints import (
    Documentation,
    Manpage,
    _ArgumentParsingAction,
    _Type,
    _TypePrinter,
)
from ...utils.datastructures import TypeDictionary
from ...utils.duckcord.color import Color2
from ...utils.duckcord.embeds import Embed2, EmbedField
from ...utils.english import QuantifiedNP, singularize, slugify
from ...utils.markdown import a, blockquote, em, pre, strong
from ...utils.memo import get_memo
from ...utils.pagination import EmbedPagination, chapterize_fields, chapterize_items
from .exceptions import BadDocumentation, MissingDescription, NoSuchCommand

CheckPredicate = Callable[[Context], bool]
CheckWrapper = Callable[[Command], Command]
CheckDecorator = Callable[..., CheckWrapper]

TypeDict = TypeDictionary[_Type, _TypePrinter]

_NOTHING = object()

log = logging.getLogger("discord.exts.autodoc")


class _EmbedField(TypedDict):
    name: str
    value: str
    inline: bool


class _Embed(TypedDict):
    title: str
    description: str
    fields: list[_EmbedField]


@runtime_checkable
class _ArgumentType(Protocol):
    key: str
    slug: str
    order: int

    is_hidden: bool
    is_unused: bool
    is_optional: bool
    is_greedy: bool

    def describe(self) -> str:
        ...

    def as_node(self) -> str:
        ...

    def to_comparable(self) -> tuple:
        ...

    def __str__(self) -> str:
        ...

    def __repr__(self) -> str:
        return self.slug

    def __lt__(self, other: _ArgumentType):
        if not isinstance(getattr(other, "order", None), int):
            return NotImplemented
        return self.order < other.order

    def __eq__(self, other: _ArgumentType):
        if not isinstance(other, _ArgumentType):
            return NotImplemented
        return self.to_comparable() == other.to_comparable()

    def __hash__(self):
        return hash(self.to_comparable())


@total_ordering
class _Argv0(_ArgumentType):
    def __init__(self, name: str) -> None:
        self.key = name
        self.slug = name
        self.order = -1
        self.is_hidden = True
        self.is_unused = False
        self.is_optional = False
        self.is_greedy = False

    def describe(self) -> str:
        return self.key

    def as_node(self) -> str:
        return self.key

    def to_comparable(self) -> tuple:
        return (self.order, self.key)

    def __str__(self) -> str:
        return self.key


@total_ordering
class Argument(_ArgumentType):
    """Represent an argument for a command.

    Argument objects keep track of the argument's name, expected types,
    default values, and displayed names in command help.

    Argument objects are populated by the Documentation class when
    it inspects a command's function signature.
    """

    def __init__(self, env: Manpage, param: Parameter) -> None:
        """Create an Argument description from an `inspect.Parameter` object."""

        annotation = param.annotation
        if annotation is Parameter.empty:
            raise BadDocumentation(f"Parameter {param.name} is not annotated")

        self.env = env
        self.key = param.name
        self.is_greedy = isinstance(annotation, type(Greedy))
        self.final = param.kind is Parameter.KEYWORD_ONLY

        self.accepts = self.infer_accepts(annotation)

        if param.default is not Parameter.empty:
            self.default = param.default
        elif self._is_optional_type(param.annotation):
            self.default = None
        else:
            self.default = _NOTHING

        if self.is_greedy:
            self.annotation = annotation.converter
        else:
            self.annotation = annotation

        self.help: str = ""
        self.description: str = ""
        self.node: str = ""
        self.signature: str = ""

        self.order: int = 0
        self.hidden: bool = False

    @property
    def is_hidden(self) -> str:
        """Whether this argument is marked as hidden or is private.

        Hidden arguments are not shown in the help page.
        """
        return self.hidden or self.key[0] == "_"

    @property
    def is_unused(self) -> bool:
        """Whether this argument is a "rest value" argument and\
        is expected to not be used.

        In discord.py, this is usually the first keyword-only argument.
        The argument is expected to not be used if it doesn't have an
        annotation or if the annotation is `str`.
        """
        return (
            self.final and self.is_optional and not self.help and not self.description
        )

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
    def _is_greedy_type(cls, annotation) -> bool:
        return isinstance(annotation, type(Greedy))

    @classmethod
    def _is_literal_type(cls, annotation) -> bool:
        return get_origin(annotation) is Literal

    @classmethod
    def _is_optional_type(cls, annotation) -> bool:
        return type(None) in get_args(annotation)

    @classmethod
    def _get_constituents(cls, annotation) -> list[_Type]:
        constituents = filter(
            lambda t: t is not type(None), get_args(annotation)  # noqa: E721
        )
        return [*split_at(constituents, cls._is_literal_type)][0]

    def describe(self) -> str:
        """Describe what this argument does and what it takes in the Argument secion."""
        if self.description:
            return self.description
        if self.is_unused:
            return "(Not used)"
        elif self.final:
            accepts = self.accepts.bare()
        elif self.is_greedy:
            accepts = self.accepts.one_or_more()
        else:
            accepts = self.accepts.a()
        if self.is_optional:
            accepts = f"{accepts}; optional"
            if self.default:
                accepts = f"{accepts}, defaults to {self.default}"
        if self.help:
            accepts = f"{self.help} Should be {accepts}"
        else:
            accepts = f"Should be {accepts}"
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
            return ""
        if self.final:
            return f"[{self.accepts.concise(1)} ...]"
        if self.is_greedy:
            return f"[one or more {self.accepts.concise(2)}]"
        return f"[{self.accepts.concise(1)}]"

    def __str__(self):
        """Print the argument's name in manpage style.

        This is used to show the command signature in the synopsis.
        """
        if self.signature:
            return self.signature
        if self.is_unused:
            return "[...]"
        if self.final:
            return f"[{self.slug} ...]"
        if self.is_greedy:
            return f"[{self.slug} {self.slug} ...]"
        if self.is_optional:
            return f"[{self.slug}]"
        return f"‹{self.slug}›"

    def to_comparable(self):
        return (
            self.order,
            self.key,
            self.default,
            self.is_greedy,
            self.final,
            type(self),
            self.annotation,
        )

    def infer_accepts(self, annotation: _Type) -> QuantifiedNP:
        """Create a phrase in natural English describing the type of info this argument expects."""
        if self._is_type_union(annotation):
            return self.infer_union_type(annotation)
        if self._is_greedy_type(annotation):
            return self.infer_accepts(annotation.converter)
        if printer := self.env.find_printer(annotation):
            if callable(printer):
                printer = printer(annotation)
            if not isinstance(printer, QuantifiedNP):
                return self.infer_accepts(printer)
            return printer
        log.warning(f"No type description for {annotation}")
        return QuantifiedNP(annotation.__name__)

    def infer_union_type(self, annotation) -> QuantifiedNP:
        """Handle Union types while describing the argument's type."""
        if self._is_optional_type(annotation):
            # Remove NoneType from optional types
            args = dict.fromkeys(get_args(annotation))
            args.pop(type(None), None)
            declared = Union.__getitem__(tuple(args.keys()))  # Silence type checker
        else:
            declared = annotation
        if printer := self.env.find_printer(declared):
            if callable(printer):
                res = printer(declared)
                if not isinstance(res, QuantifiedNP):
                    return self.infer_accepts(res)
                return res
            return printer
        if not self._is_type_union(declared):
            return self.infer_accepts(declared)
        constituents = self._get_constituents(declared)
        if len(constituents) == 1:
            return self.infer_accepts(constituents[0])
        return reduce(or_, [self.infer_accepts(t) for t in constituents])


class CommandSignature:
    """An ordered of Arguments representing one possible way to call a command.

    This object is used to format command synopsis and syntax help.
    """

    def __init__(self, arguments: tuple[_ArgumentType, ...], description: str = ""):
        self.arguments = tuple(sorted(arguments))
        self.description = description

    def as_synopsis(self) -> str:
        """Print a manpage style signature.

        For example, with a command whose function signature is

            `message(channel: Channel, *, content: Optional[str] = None)`

        This prints

            `message ‹channel› [content]`

        """
        return " ".join(filter(None, (str(arg) for arg in self.arguments)))

    def as_node(self) -> str:
        """Print the signature indicating the types of each argument.

        For example, with a command whose function signature is

            `message(channel: Channel, *, content: Optional[str] = None)`

        This prints

            `message [text channel] [text content ...]`

        """
        return " ".join(filter(None, (arg.as_node() for arg in self.arguments)))

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


def _default_arg_delimiter(idx: int, param: Parameter) -> _ArgumentParsingAction:
    if idx == 0:
        return "skip"
    if isinstance(param.annotation, type) and issubclass(param.annotation, Context):
        return "skip"
    if param.kind is Parameter.KEYWORD_ONLY:
        return "break"
    return "proceed"


class CommandDoc(Documentation):
    """Documentation objects contain all information necessary\
    to produce a detailed help page for a command.

    The autodoc module instantiates one Documentation object from one
    discord.py Command object, reading its function signature and generating
    descriptions.

    This relies on the Command callbacks being augmented with the provided decorators,
    which convey the command's description, call syntax, and usage examples, etc.

    See `autodoc.decorators` for more info.
    """

    def __init__(self, env: Manpage, cmd: Command):
        self.env = env

        self.name: str = cmd.name
        self.parent: str = cmd.full_parent_name
        self.call_sign: str = cmd.qualified_name

        self.standalone: bool = getattr(cmd, "invoke_without_command", True)
        self.aliases: list[str] = cmd.aliases

        self.description: str = "(no description)"
        self.synopsis: tuple[str, ...] = ("(no synopsis)",)
        self.examples: dict[tuple[str, ...], str] = {}
        self.discussions: dict[str, str] = {}

        self.arguments: OrderedDict[str, _ArgumentType]
        self.infer_arguments(cmd.params)

        self.invocations: OrderedDict[frozenset[str], CommandSignature]

        self.subcommands: dict[str, CommandDoc] = {}
        self.restrictions: list[str] = []

        self.hidden: bool = False
        self.invalid_syntaxes: set[frozenset[str]] = set()

        self.sections: dict[str, str] = {}
        self.frozen: bool = False

        self.export: _Embed = {}

        memo = get_memo(cmd, "__command_doc__", "_callback", default=[])
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
        return [f"{self.parent} {alias}" for alias in self.aliases]

    def iter_call_styles(
        self, options: deque[_ArgumentType] = None, stack: list[_ArgumentType] = None
    ):
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
        elif options[0].is_optional or options[0].is_greedy:
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
        should_break = False
        delimiter = self.env.get_arg_delimiter()
        for i, (k, v) in enumerate(args.items()):
            action = delimiter(i, v)
            if action == "skip":
                continue
            if action == "break":
                if should_break:
                    # At most 1 keyword-only argument allowed
                    # per command, the rest will not be handled
                    #
                    # Some commands may utilize extra keyword-only
                    # argument for hidden options only usable
                    # through direct calls
                    break
                should_break = True
            arguments[k] = Argument(self.env, v)
        arguments["__argv0__"] = _Argv0(self.call_sign)
        self.arguments = arguments

    def build_signatures(self):
        """Create a mapping of all call signatures for this command."""
        signatures = OrderedDict()
        for sig in self.iter_call_styles():
            signatures[sig.as_frozenset()] = sig
        self.invocations = signatures

    def ensure_signatures(self):
        """Build function signatures if it has not been done."""
        if not hasattr(self, "invocations"):
            self.build_signatures()

    def build_synopsis(self):
        """Format the Synopsis section."""
        lines = []
        self.ensure_signatures()
        for keys, sig in self.invocations.items():
            if keys not in self.invalid_syntaxes:
                lines.append(sig.as_synopsis())
        for subc in self.subcommands:
            lines.append(f"{subc} [...]")
        return tuple(lines)

    def format_examples(
        self,
        examples: list[tuple[str, Optional[str]]],
        transform=lambda s: strong(escape_markdown(s)),
    ) -> str:
        """Format the Examples section of the help page."""
        if not examples:
            return "(none)"
        lines = []
        for invocation, explanation in examples:
            if isinstance(invocation, tuple):
                invocation = "\n".join(invocation)
            block = transform(invocation)
            if explanation:
                block += f"\n{blockquote(explanation)}"
            lines.append(block)
        return "\x00".join(lines)

    def add_subcommand(self, command: Command, doc: CommandDoc):
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
            if printer := self.env.find_printer(deco):
                if callable(printer):
                    desc = printer(deco, **kwargs)
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
        self.synopsis = self.build_synopsis()

        sections = self.sections
        sections["Synopsis"] = pre("\n".join(self.synopsis))

        if self.aliases:
            sections["Shorthands"] = ", ".join(self.full_aliases)

        if self.examples:
            examples = self.format_examples(
                self.examples.items(),
                lambda s: "\n" + strong(s),
            )
            sections["Examples"] = examples

        invocations = {
            sig.as_node().strip(): sig.description
            for keys, sig in self.invocations.items()
            if keys not in self.invalid_syntaxes
        }
        subcommands = {
            f"{k} ...": f"{v.description} (subcommand)"
            for k, v in self.subcommands.items()
        }

        sections["Syntax"] = self.format_examples(
            {**invocations, **subcommands}.items(),
            transform=lambda s: a(strong(s), "https://."),
        )

        if self.restrictions:
            sections["Restrictions"] = "\n".join(self.restrictions)

        arguments = [
            f"{strong(arg.key)}: {arg.describe()}"
            for arg in self.arguments.values()
            if not arg.is_hidden and not arg.is_unused
        ]
        sections["Arguments"] = "\x00".join(arguments)

        for k, v in self.discussions.items():
            sections[k] = v

        self.assert_documentations()
        self.export = self.generate_help()

    def assert_documentations(self):
        """Assert that documentations must contain some required information.

        Currently, this logs a warning if the command does not have a description.
        """
        if not self.description:
            log.warning(MissingDescription(self.call_sign))

    def generate_help(self) -> dict:
        """Format the help embed and return it as a dict."""
        sections = [
            {"name": k, "value": v, "inline": False}
            for k, v in self.sections.items()
            if v
        ]
        title = f"Help: {self.call_sign}"
        return {
            "title": title,
            "description": self.description,
            "fields": sections,
        }

    def to_embed(self, maxlen: int = 500) -> EmbedPagination:
        sections = [
            EmbedField(f["name"], f["value"], False)
            for f in self.export["fields"]
            if f["value"]
        ]
        chapters = chapterize_fields(sections, maxlen, linebreak=lambda c: c == "\x00")
        embeds = [
            Embed2(fields=[c.replace("\x00", "\n") for c in chapter])
            for chapter in chapters
        ]
        title = f"Help: {self.call_sign}"
        embeds = [e.set_description(self.description) for e in embeds]
        return EmbedPagination(embeds, title, False)


class Manual(Manpage):
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

    def __init__(self):
        self._types: TypeDict = TypeDictionary()
        self._commands: dict[str, CommandDoc] = {}

        self._sections: dict[str, list[str]] = defaultdict(list)
        self._descriptions: dict[str, str] = defaultdict(str)
        self._aliases: dict[str, str] = {}

        self._toc: dict[str, str] = {}
        self._export: _Embed = {}
        self._frozen: bool = False

        self._arg_delimiter = _default_arg_delimiter

    def load_commands(self, bot: Bot) -> None:
        sections: dict[tuple[int, str], list[str]] = defaultdict(list)
        descriptions = {}
        all_commands: dict[str, Command] = {
            cmd.qualified_name: cmd for cmd in bot.walk_commands()
        }

        for call, cmd in all_commands.items():
            self._commands[call] = CommandDoc(self, cmd)
            if cmd.cog and (sort_order := getattr(cmd.cog, "sort_order", 0)):
                cog: Cog = cmd.cog
                section = (sort_order, cog.qualified_name)
                desc = cog.description
            else:
                section = (99, "Miscellaneous")
                desc = ""
            sections[section].append(call)
            descriptions[section] = desc

        for call, cmd in all_commands.items():
            parent = self._commands[cmd.qualified_name]
            subcommands: list[Command] = getattr(cmd, "commands", None) or []
            for subcmd in subcommands:
                subdoc = self._commands[subcmd.qualified_name]
                parent.add_subcommand(subcmd, subdoc)

        for (idx, k), calls in sorted(sections.items(), key=lambda t: t[0]):
            self._sections[k] = calls
            self._descriptions[k] = descriptions[idx, k]

    def finalize(self):
        """Generate all help pages and the table of content."""
        if self._frozen:
            return
        self._frozen = True
        self._propagate_restrictions(self._commands, [], set())
        self._register_aliases()
        for doc in self._commands.values():
            doc.finalize()
        for section, calls in self._sections.items():
            lines = []
            desc = self._descriptions[section]
            if desc:
                lines.append(em(desc))
            for call in sorted(calls):
                doc = self._commands[call]
                if doc.invisible:
                    continue
                lines.append(f"{strong(call)}: {doc.description}")
            content = "\n".join(lines)
            if content.strip():
                self._toc[section] = blockquote(content)

        fields = [
            {"name": k, "value": v, "inline": False} for k, v in self._toc.items()
        ]
        self._export = {"fields": fields}

    def register_type(self, type_: _Type, printer: _TypePrinter) -> None:
        self._types[type_] = printer

    def find_printer(self, type_: _Type) -> Optional[_TypePrinter]:
        return self._types.get(type_)

    def get_arg_delimiter(self):
        return self._arg_delimiter

    def set_arg_delimiter(self, delimiter) -> None:
        self._arg_delimiter = delimiter

    def _propagate_restrictions(
        self,
        tree: dict[str, CommandDoc],
        stack: list[list[str]],
        seen: set[str],
    ):
        """Include restrictions from parent commands in subcommands' help page."""
        for call_sign, doc in tree.items():
            if call_sign in seen:
                continue
            if doc.standalone:
                continue
            seen.add(call_sign)
            restrictions = [f"(Parent) {r}" for r in doc.restrictions]
            doc.restrictions.extend(chain.from_iterable(stack))
            stack.append(restrictions)
            self._propagate_restrictions(doc.subcommands, stack, seen)
            stack.pop()

    def _register_aliases(self):
        """Create a mapping of all possible command names to support lookup by aliases."""
        aliases: dict[str, list[str]] = defaultdict(list)
        for call_sign, doc in self._commands.items():
            aliased_prefixes = [*aliases[doc.parent]]
            aliased_prefixes.append(doc.parent)
            for prefix in aliased_prefixes:
                for alias in [doc.name, *doc.aliases]:
                    aliases[call_sign].append(f"{prefix} {alias}".strip())
        for call_sign, aliases_ in aliases.items():
            for alias in aliases_:
                self._aliases[alias] = call_sign

    def find_command(self, query: str, include_hidden: bool = False) -> Documentation:
        """Look up a command by name and return its documentation.

        :param query: Query to look up
        :type query: str
        :param hidden: Whether to include hidden commands, defaults to False
        :type hidden: bool, optional
        :raises NoSuchCommand: If there are no match
            (or if the matched command is hidden)
        :rtype: Documentation
        """
        doc = self._commands.get(query)
        if not doc:
            aliased = self._aliases.get(query)
            doc = self._commands.get(aliased)
        if not doc or not include_hidden and doc.invisible:
            try:
                # TODO: replace with rapidfuzz
                from rapidfuzz import process as fuzzy
                from rapidfuzz.fuzz import QRatio

                matched = fuzzy.extract(
                    query, self._commands.keys(), scorer=QRatio, score_cutoff=65
                )
            except ModuleNotFoundError:
                matched = None
            else:
                if matched:
                    for cmd, _weight in matched:
                        if cmd == query:
                            continue
                        if not include_hidden and self._commands[cmd].invisible:
                            continue
                        matched = cmd
                        break
                    else:
                        matched = None
            raise NoSuchCommand(query, matched)
        return doc

    def iter_commands(self):
        yield from sorted(self._commands.items(), key=lambda t: t[0])

    def to_embed(self, maxlen: int = 500) -> EmbedPagination:
        fields = [EmbedField(**f) for f in self._export["fields"]]
        chapters = chapterize_items(fields, maxlen)
        embeds = [Embed2(fields=chapter, color=Color2.blue()) for chapter in chapters]
        embeds = [
            e.set_footer(text=('Use "help [command]" here to see how to use a command'))
            for e in embeds
        ]
        return EmbedPagination(embeds, "Help", True)
