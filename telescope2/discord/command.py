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

from discord.ext.commands import Command, Group, command, errors, group

from telescope2.utils.functional import finalizer

from .context import Circumstances
from .utils.textutil import strong


class DocumentationMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .documentation import Documentation
        self.doc = Documentation.from_command(self)

    def _ensure_assignment_on_copy(self, copied_command):
        cmd = super()._ensure_assignment_on_copy(copied_command)
        cmd.doc = self.doc
        return cmd


class Instruction(DocumentationMixin, Command):
    async def invoke(self, ctx: Circumstances):
        try:
            return await super().invoke(ctx)
        except errors.UserInputError as exc:
            return await self.on_input_error(ctx, exc)
        except errors.CheckFailure as exc:
            return await self.on_check_violation(ctx, exc)
        except errors.CommandOnCooldown as exc:
            return await self.on_cmd_cooldown(ctx, exc)
        except errors.MaxConcurrencyReached as exc:
            return await self.on_max_concurrency(ctx, exc)

    async def on_input_error(self, ctx: Circumstances, exc: errors.UserInputError):
        return await ctx.reply(content=str(exc))

    async def on_check_violation(self, ctx: Circumstances, exc: errors.CheckFailure):
        return await ctx.reply(content=str(exc))

    async def on_cmd_cooldown(self, ctx: Circumstances, exc: errors.CommandOnCooldown):
        return await ctx.reply(content=str(exc))

    async def on_max_concurrency(self, ctx: Circumstances, exc: errors.MaxConcurrencyReached):
        return await ctx.reply(content=str(exc))


class Ensemble(DocumentationMixin, Group):
    def __init__(self, *args, case_insensitive=None, **kwargs):
        super().__init__(*args, case_insensitive=True, **kwargs)

    @finalizer
    def instruction(self, *args, **kwargs):
        return super().command(*args, cls=Instruction, **kwargs)

    def add_command(self, command: Instruction):
        super().add_command(command)
        self.doc.add_subcommand(command)
        return command


@finalizer(1)
def instruction(name: str, **kwargs) -> Instruction:
    return command(name, cls=Instruction, **kwargs)


@finalizer(1)
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
