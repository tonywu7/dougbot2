# repl.py
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

from cmd import Cmd
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from getpass import getpass
from typing import Any, Optional

from .logger import colored as _

missing = object()


@dataclass
class Question:
    """A question in a REPL form."""

    key: str
    prompt: str
    required: bool
    value: Any = missing
    converter: Callable[[str], Any] = lambda v: v
    conceal: bool = False


class TemplateQuestionMixin:
    """Mixin providing convenient methods for creating yes/no and multiple-choice questions."""

    @classmethod
    def yes_no(
        cls, key: str, prompt="Confirm?", required=True, default="yes", strict=False
    ):
        """Create a question that can be answered with yes or no."""
        return Question(
            key,
            f"{prompt} (yes or no)",
            required,
            default,
            cls._truth_converter(strict),
        )

    @classmethod
    def _format_choices(cls, numbered_choices: dict[str, int]):
        choices = [f'  {_(v, color="blue")}. {k}' for k, v in numbered_choices.items()]
        choices = "\n".join(choices)
        return choices

    @classmethod
    def multiple_choice(
        cls,
        key: str,
        choices: list[str] | dict[int, str],
        required=True,
        prefix="Choose one of the following",
        postfix: str = None,
        default=missing,
    ):
        """Create a multiple-choice question."""
        if isinstance(choices, Mapping):
            numbered_choices = {v: int(k) for k, v in choices.items()}
        else:
            numbered_choices = {c: i for i, c in enumerate(choices, start=1)}
        postfix = postfix or key
        if postfix:
            postfix = f"\n{postfix}"
        prompt = f"{prefix}\n{cls._format_choices(numbered_choices)}{postfix}"
        return Question(
            key=key,
            prompt=prompt,
            required=required,
            value=default,
            converter=cls._choice_converter(numbered_choices),
        )

    @classmethod
    def _choice_converter(cls, choices: dict[str, int]) -> Callable[[str], int]:
        def converter(t: str):
            try:
                t = int(t)
            except ValueError:
                pass
            if isinstance(t, int):
                if t not in set(choices.values()):
                    raise ValueError("Invalid option.")
                return t
            if t not in choices:
                raise ValueError("Invalid option.")
            return choices[t]

        return converter

    @classmethod
    def _truth_converter(cls, strict=False) -> Callable[[str], bool]:
        def converter(t: str) -> bool:
            if strict:
                if t == "yes":
                    return True
                if t == "no":
                    return False
                raise ValueError('Must be "yes" or "no".')
            else:
                return t[0].lower() == "y"

        return converter


class Form(TemplateQuestionMixin, Cmd):
    """Form input in the command-line."""

    def __init__(self, questions: list[Question]):
        super().__init__()
        self.filled = False
        self._form = {}
        self._questions = questions
        self._pointer = -1
        self._current: Question
        self._forward()

    @property
    def formdata(self) -> dict[str, str]:
        """Return the form data including unfilled questions as a mapping."""
        return {**self._form}

    @property
    def formdata_filled(self) -> dict[str, str]:
        """Return the form data including only filled questions."""
        return {k: v for k, v in self._form.items() if v is not missing}

    @property
    def formdata_missing(self) -> dict[str, str]:
        """Return the form data including only questions left blank."""
        return {k: v for k, v in self._form.items() if v is missing}

    @property
    def current(self) -> Question:
        """Get the currently displayed question."""
        return self._current

    def _prompt_pass(self) -> str:
        password = getpass(self.prompt)
        self.cmdqueue.append(password)

    def _set_position(self, pos: int):
        if pos < 0:
            raise IndexError
        self._current = self._questions[pos]
        self._pointer = pos
        self.prompt = self._format_prompt()
        if self._current.conceal:
            try:
                self._prompt_pass()
            except KeyboardInterrupt:
                print()
                self._backward()

    def _format_prompt(self):
        prompt = _(self.current.prompt, attrs=["bold"])
        if self.current.value is not missing and not self.current.conceal:
            return f"{prompt} [{self.current.value}] "
        return f"{prompt}: "

    def _forward(self) -> Optional[int]:
        try:
            self._set_position(self._pointer + 1)
        except IndexError:
            return 1

    def _backward(self) -> Optional[int]:
        try:
            self._set_position(self._pointer - 1)
        except IndexError:
            return 1

    def postcmd(self, should_advance: bool, line: str):
        if not should_advance:
            self._set_position(self._pointer)
            return
        stop = self._forward()
        if stop == 1:
            self.filled = True
            return True

    def emptyline(self):
        if self.current.required and self.current.value is missing:
            print("Please enter a value.")
        else:
            return self.default(self.current.value)

    def default(self, line: str):
        try:
            value = self.current.converter(line)
        except Exception as e:
            print(f"Error: {e}")
        else:
            self._form[self.current.key] = self.current.value = value
            return True

    def do_help(self, arg):
        return self.default("help")

    def cmdloop(self, intro=None):
        while True:
            try:
                return super().cmdloop(intro)
            except KeyboardInterrupt:
                print()
                stop = self._backward()
                if stop:
                    return

    def __repr__(self):
        return f"{type(self).__name__} {id(self)}"
