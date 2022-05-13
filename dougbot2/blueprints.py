# protocols.py
# Copyright (C) 2022  @tonyzbf +https://github.com/tonyzbf/
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

from datetime import datetime
from inspect import Parameter
from typing import (
    Any,
    AsyncContextManager,
    Awaitable,
    Callable,
    Iterable,
    Literal,
    Optional,
    Protocol,
    Tuple,
    Type,
    TypeVar,
    TypedDict,
    Union,
)

from aiohttp import ClientSession
from discord import Color, File, Guild, Member, Message, TextChannel, User
from discord.abc import Messageable
from discord.ext.commands import Bot, Command, Context, Converter

from dougbot2.defaults import Styles
from dougbot2.utils.pagination import EmbedPagination

from .utils.duckcord import Embed2
from .utils.english import QuantifiedNP
from .utils.response import ResponseInit

T = TypeVar("T")


class Console(Protocol):
    def debug(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[BaseException] = None,
        embed: Optional[Embed2] = None,
        **kwargs: Any,
    ) -> Awaitable[Optional[Message]]:
        ...

    def info(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[BaseException] = None,
        embed: Optional[Embed2] = None,
        **kwargs: Any,
    ) -> Awaitable[Optional[Message]]:
        ...

    def warning(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[BaseException] = None,
        embed: Optional[Embed2] = None,
        **kwargs: Any,
    ) -> Awaitable[Optional[Message]]:
        ...

    def error(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[BaseException] = None,
        embed: Optional[Embed2] = None,
        **kwargs: Any,
    ) -> Awaitable[Optional[Message]]:
        ...

    def critical(
        self,
        msg: str,
        *args: Any,
        exc_info: Optional[BaseException] = None,
        embed: Optional[Embed2] = None,
        **kwargs: Any,
    ) -> Awaitable[Optional[Message]]:
        ...

    def log(
        self,
        level: int,
        msg: str,
        *args: Any,
        exc_info: Optional[BaseException] = None,
        embed: Optional[Embed2] = None,
        **kwargs: Any,
    ) -> Awaitable[Optional[Message]]:
        ...


class _Surroundings(Protocol):
    me: Union[Member, User]
    message: Union[Message, Messageable]
    timestamp: datetime

    invoked_with: str
    invoked_parents: list[str]
    invoked_subcommand: Optional[Command]
    subcommand_passed: Optional[str]

    author: Union[Member, Messageable]
    guild: Guild
    channel: TextChannel

    bot: MissionControl
    prefix: str

    command: Optional[Command]

    raw_input: str
    is_direct_message: bool

    styles: Styles

    def respond(
        self,
        content: Optional[str] = None,
        embed: Optional[Embed2] = None,
        files: Optional[list[File]] = None,
        nonce: Optional[int] = None,
    ) -> ResponseInit:
        ...

    def get_logger(self) -> Console:
        ...

    def call(self, cmd: Command, *args: Any, **kwargs: Any) -> Awaitable[Any]:
        ...

    def set_cooldown(self, cmd: Command) -> None:
        ...

    def concurrently(self, cmd: Command) -> AsyncContextManager[None]:
        ...


_ExceptionType = Union[Type[Exception], Tuple[Type[Exception], ...]]
_ExceptionHandler = Callable[[_Surroundings, Exception], Awaitable[Optional[str]]]


class _ExceptionResult(TypedDict):
    title: str
    description: str


_Type = Union[type, Converter, type[Converter], Callable]
_TypeHint = Union[str, QuantifiedNP]

_ArgumentParsingAction = Literal["skip", "proceed", "break"]
_ArgumentDelimiter = Callable[[int, Parameter], _ArgumentParsingAction]


class Documentation(Protocol):
    def to_embed(self) -> EmbedPagination:
        ...


class Manpage(Protocol):
    def get_arg_delimiter(self) -> _ArgumentDelimiter:
        ...

    def set_arg_delimiter(self, delimiter: _ArgumentDelimiter) -> None:
        ...

    def register_type(self, type_: _Type, printer: _TypePrinter) -> None:
        ...

    def load_commands(self, bot: Bot) -> None:
        ...

    def finalize(self) -> None:
        ...

    def find_printer(self, type_: _Type) -> Optional[_TypePrinter]:
        ...

    def find_command(self, query: str, include_hidden: bool = False) -> Documentation:
        ...

    def iter_commands(self) -> Iterable[tuple[str, Documentation]]:
        ...

    def to_embed(self) -> EmbedPagination:
        ...


_TypePrinter = Union[_TypeHint, Callable[[_Type], Union[_Type, _TypeHint]]]


class ErrorPage(Protocol):
    def get_error(
        self, ctx: Surroundings, exc: Exception
    ) -> Awaitable[Optional[_ExceptionResult]]:
        ...

    def set_error_blurb(self, exc: _ExceptionType, blurb: _ExceptionHandler) -> None:
        ...

    def add_error_fluff(self, exc: _ExceptionType, *fluff: str) -> None:
        ...

    @classmethod
    def exception_to_str(cls, ctx: Surroundings, exc: Exception) -> Awaitable[str]:
        ...


class LoggingAmenities(Protocol):
    def register_logger(
        self,
        name: str,
        *exc_classes: type[Exception],
        title: str,
        level: int = 20,
        show_stacktrace: bool = False,
    ):
        ...

    def ignore_exception(self, *exc: Type[Exception]) -> None:
        ...

    def get_logger(self, name: str, guild: Guild) -> Console:
        ...

    def dump_traceback(self, exc: BaseException) -> File:
        ...

    def pprint_exception(
        self, exc: Exception, color: Optional[Color] = None, title: Optional[str] = None
    ) -> Embed2:
        ...

    def log_exception(self, ctx: Surroundings, exc: Exception) -> Awaitable[None]:
        ...


BotOption = Literal["set_presence"]


class _MissionControl(Protocol):
    def get_web_client(self) -> ClientSession:
        ...

    def get_cache(self, default: Optional[T] = None, /, **keys: Any) -> Optional[T]:
        ...

    def set_cache(self, value: Any, ttl: Optional[float] = 300, /, **keys: Any) -> None:
        ...

    def del_cache(self, **keys: Any) -> None:
        ...

    def get_option(self, key: BotOption, default: Optional[T] = None) -> Optional[T]:
        ...

    def defer_init(self, callback: Callable[[], None]) -> None:
        ...

    manpage: Manpage
    errorpage: ErrorPage
    console: LoggingAmenities


# Would be cool if we had intersection types


class Surroundings(_Surroundings, Context):
    pass


class MissionControl(_MissionControl, Bot):
    pass
