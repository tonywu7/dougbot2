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

import attr
from discord.ext.commands import Bot, Command, Context
from fuzzywuzzy import process as fuzzy
from more_itertools import flatten

from ...utils.duckcord.embeds import Embed2, EmbedField
from ...utils.markdown import blockquote, em, strong
from ...utils.pagination import (EmbedPagination, TextPagination,
                                 chapterize_items)
from .documentation import Documentation
from .exceptions import NoSuchCommand


@attr.s
class Manual:
    MANPAGE_MAX_LEN = 1000

    commands: dict[str, Documentation] = attr.ib(factory=dict)
    sections: dict[str, list[str]] = attr.ib(factory=lambda: defaultdict(list))
    descriptions: dict[str, str] = attr.ib(factory=lambda: defaultdict(str))
    aliases: dict[str, str] = attr.ib(factory=dict)

    toc: dict[str, str] = attr.ib(factory=dict)
    toc_rich: EmbedPagination = attr.ib(default=None)
    toc_text: TextPagination = attr.ib(default=None)

    frozen: bool = attr.ib(default=False)

    @classmethod
    def from_bot(cls, bot: Bot):
        man = Manual()
        sections: dict[tuple[int, str], list[str]] = defaultdict(list)
        descriptions = {}
        all_commands: dict[str, Command] = {
            cmd.qualified_name: cmd for cmd
            in bot.walk_commands()
            if not cmd.hidden
        }

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
        for section, calls in self.sections.items():
            lines = []
            desc = self.descriptions[section]
            if desc:
                lines.append(em(desc))
            for call in sorted(calls):
                doc = self.commands[call]
                if doc.hidden or not doc.standalone:
                    continue
                lines.append(f'{strong(call)}: {doc.description}')
            content = '\n'.join(lines)
            if content.strip():
                self.toc[section] = blockquote(content)

        fields = [EmbedField(k, v, False) for k, v in self.toc.items()]
        chapters = chapterize_items(fields, self.MANPAGE_MAX_LEN)
        embeds = [Embed2(fields=chapter) for chapter in chapters]
        self.toc_rich = EmbedPagination(embeds, 'Command list', True)

        fields = [f'{strong(k)}\n{v}' for k, v in self.toc.items()]
        chapters = chapterize_items(fields, self.MANPAGE_MAX_LEN)
        texts = ['\n\n'.join(chapter) for chapter in chapters]
        self.toc_text = TextPagination(texts, 'Command list')

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

    async def send_toc(self, ctx: Context):
        front_embed = self.toc_rich[0][1]
        front_text = self.toc_text[0][0]
        msg, embed_sent = await ctx.reply_with_text_fallback(front_embed, front_text)
        if not embed_sent:
            pagination = self.toc_text
        else:
            pagination = self.toc_rich
        paginator = pagination(ctx.bot, msg, 60, ctx.author.id)
        await paginator.run()
