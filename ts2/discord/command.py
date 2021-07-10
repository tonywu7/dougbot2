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

from discord.ext.commands import CheckFailure, Command, Group, command, group

from ts2.utils.functional import memoize

from .context import Circumstances
from .utils.markdown import strong


class DocumentationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .documentation import Documentation
        self.doc = Documentation.from_command(self)

    def _ensure_assignment_on_copy(self, copied_command):
        cmd = super()._ensure_assignment_on_copy(copied_command)
        cmd.doc = self.doc
        return cmd


class OptionsMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .parse import build_parser
        build_parser(self)


class Instruction(DocumentationMixin, Command):
    dm_command = False


class Ensemble(DocumentationMixin, Group):
    def __init__(self, *args, case_insensitive=None, **kwargs):
        super().__init__(*args, case_insensitive=True, **kwargs)

    def instruction(self, *args, **kwargs):
        return super().command(*args, cls=Instruction, **kwargs)

    def ensemble(self, *args, cls=None, **kwargs):
        return super().group(*args, cls=type(self), **kwargs)

    def add_command(self, command: Instruction):
        super().add_command(command)
        self.doc.add_subcommand(command)
        return command


def dm_command():
    def wrapper(f: Instruction):
        f.dm_command = True
        return f

    def deco(obj):
        return memoize(obj, '__command_doc__', wrapper)
    return deco


async def command_environment_check(ctx: Circumstances):
    if not (ctx.command.dm_command ^ bool(ctx.guild)):
        raise EnvironmentMismatch()


def instruction(name: str, **kwargs) -> Instruction:
    return command(name, cls=Instruction, **kwargs)


def ensemble(name: str, invoke_without_command=False, **kwargs) -> Ensemble:
    return group(name, cls=Ensemble, invoke_without_command=invoke_without_command, **kwargs)


class NoSuchCommand(ValueError):
    def __init__(self, query: str, potential_match: str = None, *args: object) -> None:
        super().__init__(*args)
        if potential_match:
            self.message = f'No command named {strong(query)}. Did you mean {strong(potential_match)}?'
        else:
            self.message = f'No command named {strong(query)}.'

    def __str__(self) -> str:
        return self.message


class EnvironmentMismatch(CheckFailure):
    def __init__(self, message=None, *args):
        super().__init__(message='Server vs. DM commands misused', *args)
