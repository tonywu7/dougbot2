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

from contextlib import asynccontextmanager

from discord.ext.commands import Command, Group, command, group


class Instruction(Command):
    def __init__(self, *args, unreachable: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.unreachable = unreachable

    @asynccontextmanager
    async def acquire_concurrency(self, ctx):
        try:
            if self._max_concurrency is not None:
                await self._max_concurrency.acquire(ctx)
            yield
        finally:
            if self._max_concurrency is not None:
                await self._max_concurrency.release(ctx)

    def trigger_cooldowns(self, ctx):
        self._prepare_cooldowns(ctx)


class Ensemble(Instruction, Group):
    def __init__(self, *args, case_insensitive=None, **kwargs):
        super().__init__(*args, case_insensitive=True, **kwargs)

    def instruction(self, *args, **kwargs):
        return super().command(*args, cls=Instruction, **kwargs)

    def ensemble(self, *args, cls=None, **kwargs):
        return super().group(*args, cls=type(self), **kwargs)


def instruction(name: str, **kwargs) -> Instruction:
    return command(name, cls=Instruction, **kwargs)


def ensemble(name: str, invoke_without_command=False, **kwargs) -> Ensemble:
    return group(name, cls=Ensemble, invoke_without_command=invoke_without_command, **kwargs)
