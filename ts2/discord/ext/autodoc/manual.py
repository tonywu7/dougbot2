# manual.py
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

from collections import defaultdict
from collections.abc import Callable
from itertools import chain
from typing import Optional

import attr
from discord.ext.commands import Bot, Command, Context
from duckcord.color import Color2
from duckcord.embeds import Embed2, EmbedField

from ...utils.common import is_direct_message
from ...utils.events import DeleteResponder, start_responders
from ...utils.markdown import blockquote, em, strong
from ...utils.pagination import EmbedPagination, chapterize_items
from ...utils.response import ResponseInit
from .documentation import Documentation
from .exceptions import NoSuchCommand

get_manual: Callable[[Context], Manual] = None


@attr.s
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

    MANPAGE_MAX_LEN = 1280

    commands: dict[str, Documentation] = attr.ib(factory=dict)
    sections: dict[str, list[str]] = attr.ib(factory=lambda: defaultdict(list))
    descriptions: dict[str, str] = attr.ib(factory=lambda: defaultdict(str))
    aliases: dict[str, str] = attr.ib(factory=dict)

    toc: dict[str, str] = attr.ib(factory=dict)
    toc_rich: EmbedPagination = attr.ib(default=None)

    title: str = attr.ib(default='Command help')
    color: Color2 = attr.ib(default=Color2.blue())

    frozen: bool = attr.ib(default=False)

    @classmethod
    def from_bot(cls, bot: Bot):
        """Instantiate a Manual from a Bot instance whose commands are fully registered."""
        man = Manual()
        sections: dict[tuple[int, str], list[str]] = defaultdict(list)
        descriptions = {}
        all_commands: dict[str, Command] = {cmd.qualified_name: cmd for cmd
                                            in bot.walk_commands()}

        for call, cmd in all_commands.items():
            man.commands[call] = Documentation.from_command(cmd)
            if cmd.cog:
                cog = cmd.cog
                section = (getattr(cog, 'sort_order', 0), cog.qualified_name)
                desc = cmd.cog.description
            else:
                section = (99, 'Miscellaneous')
                desc = ''
            sections[section].append(call)
            descriptions[section] = desc

        for call, cmd in all_commands.items():
            parent = man.commands[cmd.qualified_name]
            subcommands: list[Command] = getattr(cmd, 'commands', None) or []
            for subcmd in subcommands:
                subdoc = man.commands[subcmd.qualified_name]
                parent.add_subcommand(subcmd, subdoc)

        for (idx, k), calls in sorted(sections.items(), key=lambda t: t[0]):
            man.sections[k] = calls
            man.descriptions[k] = descriptions[idx, k]

        return man

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

        fields = [EmbedField(k, v, False) for k, v in self.toc.items()]
        chapters = chapterize_items(fields, self.MANPAGE_MAX_LEN)
        embeds = [Embed2(fields=chapter, color=self.color)
                  for chapter in chapters]
        embeds = [e.set_footer(text=('Use "help [command]" here to see'
                                     ' how to use a command'))
                  for e in embeds]
        self.toc_rich = EmbedPagination(embeds, self.title, True)

    def lookup(self, query: str, hidden=False) -> Documentation:
        """Look up a command by name and return its documentation

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

    def hidden_commands(self) -> dict[str, Documentation]:
        """Get all registered hidden commands as a mapping."""
        return {k: v for k, v in self.commands.items() if v.hidden}

    async def send_toc(self, ctx: Context):
        """Send a list of all commands to the author of this Context via DM."""
        front_embed = self.toc_rich[0][1]
        msg = await ctx.author.send(embed=front_embed)
        if not is_direct_message(ctx):
            await ctx.send('Mail has been delivered!', delete_after=20)
        pagination = self.toc_rich
        paginator = pagination(ctx.bot, msg, 300, ctx.author.id)
        deleter = DeleteResponder(ctx, msg)
        start_responders(paginator, deleter)

    async def do_help(self, ctx: Context, query: Optional[str] = None):
        """Reference callback of a help command.

        Bots implementing their help command can call this method directly.
        """
        if not query:
            return await self.send_toc(ctx)
        query = query.lower().removeprefix(ctx.prefix)
        show_hidden = await ctx.bot.is_owner(ctx.author)
        try:
            doc = self.lookup(query, show_hidden)
        except NoSuchCommand as exc:
            return await ctx.send(str(exc), delete_after=60)
        rich_help = doc.rich_help
        (await ResponseInit(ctx, embed=rich_help).reply()
         .responder(rich_help.with_context(ctx))
         .deleter().run())

    def is_hidden(self, cmd: Command):
        """Check if this command is hidden."""
        return self.commands[cmd.qualified_name].invisible


def set_manual_getter(getter: Callable[[Context], Manual]):
    # TODO: Remove
    global get_manual
    get_manual = getter


def init_bot(bot: Bot, title: str = 'Command list',
             color: Optional[int] = None) -> Manual:
    """Helper method to initialize the docs for a bot instance."""
    manual = Manual.from_bot(bot)
    manual.title = title
    if color:
        manual.color = color
    manual.finalize()
    bot.manual = manual
    set_manual_getter(lambda ctx: ctx.bot.manual)
    return manual
