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

from discord.ext.commands.errors import BadArgument, UserInputError
from discord.utils import escape_markdown

from ...utils.markdown import strong


class BadDocumentation(UserWarning):
    def __str__(self) -> str:
        return f'Bad documentation: {self.message}'


class MissingDescription(BadDocumentation):
    def __init__(self, call_sign: str) -> None:
        self.message = f'{call_sign}: No description provided'


class MissingExamples(BadDocumentation):
    def __init__(self, call_sign: str) -> None:
        self.message = f'{call_sign}: No command example provided'


class SendHelp(UserInputError):
    def __init__(self, category='normal', *args):
        self.category = category
        super().__init__(message=None, *args)


class NotAcceptable(UserInputError):
    def __init__(self, message, *args):
        super().__init__(message=message, *args)


class NoSuchCommand(ValueError):
    def __init__(self, query: str, potential_match: str = None, *args: object) -> None:
        super().__init__(*args)
        if potential_match:
            self.message = f'No command named {strong(escape_markdown(query))}. Did you mean {strong(potential_match)}?'
        else:
            self.message = f'No command named {strong(escape_markdown(query))}.'

    def __str__(self) -> str:
        return self.message


class ReplyRequired(BadArgument):
    def __call__(self):
        return super().__call__(message='You need to call this command while replying to a message.')
