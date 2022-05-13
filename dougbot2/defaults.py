# defaults.py
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

from contextlib import suppress
from pathlib import Path
from typing import Callable, Optional, TypeVar

import emoji
import toml
from attr import define, field
from discord import AllowedMentions
from django.conf import settings

from .utils.duckcord import Color2, Permissions2

T = TypeVar("T")


def unpacking(init: Callable[..., T]) -> Callable[[dict], T]:
    return lambda data: init(**data)


@define
class _Auth:
    bot_token: str
    client_id: str
    client_secret: str
    allowed_guilds: list[int]


@define
class _Default:
    prefix: str
    permission: Permissions2 = field(converter=Permissions2)
    mentions: AllowedMentions = field(converter=unpacking(AllowedMentions))

    nltk_data: str


@define
class _About:
    branding: str
    description: str
    twitter: str


@define
class _Colors:
    accent: Color2 = field(converter=Color2)


class _Emotes:
    failure: str
    pending: str
    removal: str
    success: str
    warning: str

    forward: str
    rewind: str
    head: str
    tail: str

    green: str
    red: str
    yellow: str

    def __init__(self, **emotes: str):
        for k, v in emotes.items():
            e = emoji.emojize(v)
            if e == v:
                raise ValueError(
                    f"Loading config.toml: cannot convert {v} to a valid emoji."
                    " See https://carpedm20.github.io/emoji/all.html",
                )
            setattr(self, k, e)


@define
class Styles:
    colors: _Colors = field(converter=unpacking(_Colors))
    emotes: _Emotes = field(converter=unpacking(_Emotes))


@define
class Defaults:
    auth: _Auth = field(converter=unpacking(_Auth))
    default: _Default = field(converter=unpacking(_Default))
    about: _About = field(converter=unpacking(_About))
    styles: Styles = field(converter=unpacking(Styles))


_config: Optional[Defaults] = None


def _get_instance_dir() -> Path:
    return settings.INSTANCE_DIR


def _get_project_dir() -> Path:
    return settings.PROJECT_DIR


def _load_defaults() -> Defaults:
    data: Optional[dict] = None
    config_path = _get_instance_dir() / "config.toml"
    default_config_path = _get_project_dir() / "config-default.toml"
    with suppress(toml.TomlDecodeError, OSError), open(config_path) as f:
        data = toml.load(f)
    if not data:
        with suppress(toml.TomlDecodeError, OSError), open(default_config_path) as f:
            data = toml.load(f)
    if data is None:
        raise RuntimeError(
            "Cannot load program constants from either"
            f" {config_path} or {default_config_path}.",
        )
    global _config
    _config = Defaults(**data)
    return _config


def get_defaults() -> Defaults:
    if _config is None:
        return _load_defaults()
    return _config
