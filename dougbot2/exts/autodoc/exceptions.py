# exceptions.py
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

from discord.ext.commands import UserInputError
from discord.utils import escape_markdown

from ...utils.markdown import strong


class BadDocumentation(UserWarning):
    """Warning used internally to indicate missing documentation info."""

    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return f"Bad documentation: {self.message}"


class MissingDescription(BadDocumentation):
    """Warning used internally to indicate missing documentation description."""

    def __init__(self, call_sign: str) -> None:
        self.message = f"{call_sign}: No description provided"


class MissingExamples(BadDocumentation):
    """Warning used internally to indicate missing documentation examples."""

    def __init__(self, call_sign: str) -> None:
        self.message = f"{call_sign}: No command example provided"


class NoSuchCommand(UserInputError):
    """Exception raised by a Manual object when it fails to look up a command."""

    def __init__(self, query: str, potential_match: str = None, *args: object) -> None:
        super().__init__(*args)
        if potential_match:
            self.message = f"No command named {strong(escape_markdown(query))}. Did you mean {strong(potential_match)}?"
        else:
            self.message = f"No command named {strong(escape_markdown(query))}."

    def __str__(self) -> str:
        return self.message


class NoSuchSignature(IndexError):
    def __init__(
        self,
        name: str,
        arguments: tuple[str, ...],
        candidates: list[tuple[str, ...]],
        origin: str,
    ) -> None:
        candidates = ", ".join(
            [self._make_signature(name, args) for args in candidates]
        )
        super().__init__(
            f"In {origin}:\nCommand signature"
            f" {self._make_signature(name, arguments)} doesn't exist."
            f" Candidates are {candidates}.",
        )

    def _make_signature(self, name: str, arguments: tuple[str, ...]):
        name = name.replace(" ", ".")
        signature = "".join([f"{arg}:" for arg in arguments])
        return f"{name}({signature})"


class NoSuchArgument(IndexError):
    def __init__(
        self,
        name: str,
        argument: str,
        candidates: list[str],
        origin: str,
    ):
        super().__init__(
            f"In {origin}:\n"
            f"Command {name.replace(' ', '.')} has no argument {argument}."
            f" Candidates are {candidates}."
        )
