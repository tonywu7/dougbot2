# MIT License
#
# Copyright (c) 2021 @tonyzbf +https://github.com/tonyzbf/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

import attr
from discord import Colour, Embed, Guild, Member, User

T = TypeVar('T')

_EMPTY = Embed.Empty
_EmptyType = type(_EMPTY)


def _is_empty(v: _EmptyType | None) -> bool:
    return v is None or type(v) is _EmptyType


def utcnow() -> datetime:
    """Return an aware `datetime` set to current UTC time."""
    return datetime.now(tz=timezone.utc)


class _Serializable:
    @classmethod
    def instantiate(cls, info: dict):
        if _is_empty(info):
            return _EMPTY
        if isinstance(info, cls):
            return info
        try:
            return cls(**info)
        except Exception as e:
            raise ValueError(f'Cannot convert {info} to {cls}') from e

    def to_dict(self) -> dict:
        return attr.asdict(self, recurse=True, filter=attr.filters.exclude(type(Embed.Empty)))

    def for_json(self) -> dict:
        return self.to_dict()


def _optional_convert(converter: Callable[[], T]) -> Callable[[Any], T]:
    def convert(v) -> T:
        if _is_empty(v):
            return _EMPTY
        return converter(v)
    return convert


def _datetime_convert(d: str | datetime | _EMPTY | None) -> datetime:
    if not d or isinstance(d, datetime):
        return d
    return datetime.fromisoformat(d)


@attr.s(slots=True, eq=True, frozen=True)
class EmbedField(_Serializable):
    name: str = attr.ib(converter=str)
    value: str = attr.ib(converter=str)
    inline: bool = attr.ib(converter=_optional_convert(bool), default=False)

    def __len__(self):
        return len(self.name) + len(self.value)


@attr.s(slots=True, eq=True, frozen=True)
class EmbedAuthor(_Serializable):
    name: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    icon_url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    proxy_icon_url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)

    def __len__(self):
        return len(self.name)


@attr.s(slots=True, eq=True, frozen=True)
class EmbedProvider(_Serializable):
    name: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)


@attr.s(slots=True, eq=True, frozen=True)
class EmbedAttachment(_Serializable):
    url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    proxy_url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    height: int = attr.ib(converter=_optional_convert(int), default=_EMPTY)
    width: int = attr.ib(converter=_optional_convert(int), default=_EMPTY)


@attr.s(slots=True, eq=True, frozen=True)
class EmbedFooter(_Serializable):
    text: str = attr.ib(converter=str)
    icon_url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    proxy_icon_url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)

    def __len__(self):
        return len(self.text)


@attr.s(slots=True, eq=True, frozen=True)
class Embed2:
    """attr.s dataclass. Replaces :class:`discord.Embed`.

    **Drop-in replacement for** :class:`discord.Embed` **when passed to**
    :meth:`discord.abc.Messageable.send` (which only needs :meth:`to_dict`).

    Unlike :class:`discord.Embed`, :class:`Embed2` objects are fully immutable,
    including nested data structures such as the field list.
    All "mutation" methods return a new instance instead of modifying self.
    :class:`Embed2` thus behaves a lot like ``pandas.DataFrame`` (with
    ``inplace=False``) and Django ORM's ``QuerySet``:

    .. code-block:: python

        command_help = (
            Embed2(title='Help')
            .set_description('Syntax: -help `command`')
            .add_field(name='Version', value=__version__, inline=False)
            .set_footer(text='manpage generator v0.1')
            .set_thumbnail(url=thumb_url)
        )

        prefix_help = (
            command_help
            .set_author(name=ctx.me.display_name, icon_url=ctx.me.avatar_url)
            .add_field(name='Syntax', value='prefix')
            .add_field(name='Usage', value='See current prefix.')
            .set_timestamp(utcnow())
        )  # command_help remains unchanged and can be reused

        ping_help = (
            command_help
            .set_timestamp(utcnow())
            # ...
        )

    The fluent syntax is therefore significantly more useful, in that an embed
    "template" can be created once and stored, and reused again; new embeds can
    be derived from the template, updating info (such as timestamp) as needed,
    without the need to manually call :meth:`discord.Embed.copy`.
    """
    timestamp: datetime = attr.ib(factory=lambda: _EMPTY, converter=_datetime_convert, validator=attr.validators.instance_of((datetime, type(_EMPTY))))
    color: Colour = attr.ib(converter=_optional_convert(lambda c: c if isinstance(c, Colour) else Colour(int(c))),
                            factory=Colour.default)

    fields: tuple[EmbedField] = attr.ib(factory=tuple, converter=lambda t: tuple(EmbedField.instantiate(d) for d in t))

    title: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    description: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)
    url: str = attr.ib(converter=_optional_convert(str), default=_EMPTY)

    author: EmbedAuthor = attr.ib(converter=EmbedAuthor.instantiate, default=_EMPTY)
    footer: EmbedFooter = attr.ib(converter=EmbedFooter.instantiate, default=_EMPTY)

    image: EmbedAttachment = attr.ib(converter=EmbedAttachment.instantiate, default=_EMPTY)
    thumbnail: EmbedAttachment = attr.ib(converter=EmbedAttachment.instantiate, default=_EMPTY)
    video: EmbedAttachment = attr.ib(converter=EmbedAttachment.instantiate, default=_EMPTY)
    provider: EmbedProvider = attr.ib(converter=EmbedProvider.instantiate, default=_EMPTY)

    type: str = attr.ib(default='rich')

    @property
    def colour(self):
        return self.color

    @classmethod
    def upgrade(cls, embed: Embed) -> Embed2:
        """Convert a native :class:`discord.Embed` to an :class:`Embed2` object.

        All data are deep-copied (nested structures are auto-converted to other
        supporting ``attrs`` dataclasses that are also immutable).

        :param embed: An object of the original :class:`discord.Embed` class.
        :type embed: :class:`discord.Embed`
        :return: The resulting :class:`Embed2` object.
        :rtype: :class:`Embed2`
        """
        return Embed2(**embed.to_dict())

    @classmethod
    def from_dict(cls, data: dict) -> Embed2:
        """Convert a mapping in Discord's format to an :class:`Embed2` object.

        All data are deep-copied (nested structures are auto-converted to other
        supporting ``attrs`` dataclasses that are also immutable).

        :param data: A dictionary containing embed data.
        :type data: :class:`collections.abc.Mapping`
        :return: The resulting :class:`Embed2` object.
        :rtype: :class:`Embed2`
        """
        return Embed2(**data)

    def to_dict(self) -> dict:
        """Serialize the embed to a :class:`dict`.

        :return: The result dictionary
        :rtype: :class:`dict`
        """
        info = attr.asdict(self, recurse=True, filter=attr.filters.exclude(type(Embed.Empty)))

        timestamp = self.timestamp
        if isinstance(timestamp, datetime):
            info['timestamp'] = timestamp.isoformat()

        color = self.color
        if isinstance(color, Colour):
            info['color'] = color.value

        return info

    def copy(self) -> Embed2:
        """Return a copy of this embed object.

        This is only for interoperability with existing code that may call
        :class:`discord.Embed.copy`. Since :class:`Embed2` are always immutable,
        you rarely need to call :meth:`copy` directly.

        :return: A new :class:`Embed2` object with the same content.
        :rtype: :class:`Embed2`
        """
        return attr.evolve(self)

    def add_field(self, *, name: str, value: str, inline: bool = True) -> Embed2:
        """Return a new embed with a field appended.

        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        fields = [*self.fields, EmbedField(name=name, value=value, inline=inline)]
        return attr.evolve(self, fields=fields)

    def insert_field_at(self, index: int, *, name: str, value: str, inline: bool = True) -> Embed2:
        """Return a new embed with a field inserted at ``index``.

        Field ``n`` becomes field ``n + 1`` after insert. If the index is
        out of range, insert at the end (instead of raising :exc:`IndexError`).
        A negative index is acceptable and has the same semantic as a negative
        index lookup.

        :param index: The position at which to insert a new field.
        :type index: :class:`int`
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        fields = [*self.fields[:index], EmbedField(name=name, value=value, inline=inline), *self.fields[index:]]
        return attr.evolve(self, fields=fields)

    def set_field_at(self, index: int, *, name: str, value: str, inline: bool = True) -> Embed2:
        """Return a new embed with the field at ``index`` replaced.

        If the index is out of range, a new field will be inserted at the end
        (instead of raising :exc:`IndexError`).
        A negative index is acceptable and has the same semantic as a negative
        index lookup.

        :param index: The position at which a field is to be replaced.
        :type index: :class:`int`
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        fields = [*self.fields[:index], EmbedField(name=name, value=value, inline=inline), *self.fields[index + 1:]]
        return attr.evolve(self, fields=fields)

    def get_field_value(self, key: str, default: T = '') -> str | T:
        """Return the value of the embed field with name ``key`` if it is found,\
            otherwise return ``default``.
        """
        for f in self.fields:
            if f.name == key:
                return f.value
        return default

    def clear_fields(self) -> Embed2:
        """Return a new embed with no field.

        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        return attr.evolve(self, fields=())

    def set_timestamp(self, timestamp: datetime | None = attr.NOTHING) -> Embed2:
        """Return a new embed with timestamp set.

        Pass :data:`None` to remove the timestamp. Pass no argument to set
        timestamp to current UTC time.

        :param timestamp: The timestamp to set, or :data:`None`
        :type timestamp: :class:`datetime.datetime` or :class:`NoneType`
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        if timestamp is attr.NOTHING:
            return attr.evolve(self, timestamp=utcnow())
        elif timestamp is None:
            return attr.evolve(self, timestamp=_EMPTY)
        return attr.evolve(self, timestamp=timestamp)

    def set_author(self, *, name: str | None, url: str = _EMPTY, icon_url: str = _EMPTY) -> Embed2:
        """Return a new embed with author info set.

        Pass ``name=None`` to remove the author field.

        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        return attr.evolve(self, author=EmbedAuthor(name, url, icon_url))

    def remove_author(self) -> Embed2:
        """Return a new embed with no author information.

        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        return attr.evolve(self, author=_EMPTY)

    def set_footer(self, *, text: str | None, icon_url=_EMPTY) -> Embed2:
        """Return a new embed containing the supplied footer.

        Pass ``text=None`` to remove the footer.

        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        if not text:
            return attr.evolve(self, footer=_EMPTY)
        return attr.evolve(self, footer=EmbedFooter(text, icon_url))

    def set_image(self, *, url: str | None) -> Embed2:
        return attr.evolve(self, image=EmbedAttachment(url) if url else _EMPTY)

    def set_video(self, *, url: str | None) -> Embed2:
        return attr.evolve(self, video=EmbedAttachment(url) if url else _EMPTY)

    def set_thumbnail(self, *, url: str | None) -> Embed2:
        return attr.evolve(self, thumbnail=EmbedAttachment(url) if url else _EMPTY)

    def set_color(self, color: int | Colour | None) -> Embed2:
        return attr.evolve(self, color=color)

    def set_title(self, title: str | None) -> Embed2:
        return attr.evolve(self, title=title)

    def set_description(self, description: str | None) -> Embed2:
        return attr.evolve(self, description=description)

    def set_url(self, url: str | None) -> Embed2:
        return attr.evolve(self, url=url)

    def set_provider(self, name: str = _EMPTY, url: str = _EMPTY) -> Embed2:
        return attr.evolve(self, provider=EmbedProvider(name=name, url=url))

    def use_as_author(self, user: User):
        """Return a new embed with the author set using the user's username\
            and avatar.

        :param user: The user to use.
        :type user: :class:`discord.User`
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        return self.set_author(name=str(user), icon_url=user.avatar_url)

    def use_member_color(self, member: Member):
        """Return a new embed with color set to the member's visible color in\
            the current server.

        :param person: The member to use.
        :type person: :class:`discord.Member`
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        return self.set_color(member.color)

    def personalized(self, person: User | Member, *, url: str = _EMPTY):
        """Return a new embed personalized using the user's name, avatar, and\
            color.

        :param person: The user or member to use.
        :type person: :class:`discord.User` | :class:`discord.Member`
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        author = EmbedAuthor(name=str(person), url=url,
                             icon_url=person.avatar_url)
        return attr.evolve(self, author=author, color=person.color)

    def decorated(self, guild: Guild, *, url: str = _EMPTY):
        """Return a new embed stylized using the guild's name and icon.

        :param guild: The guild to use.
        :type guild: :class:`discord.Guild`
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        author = EmbedAuthor(name=str(guild), url=url,
                             icon_url=guild.icon_url)
        return attr.evolve(self, author=author)

    def set_author_url(self, url: str | None) -> Embed2:
        """Update the author URL.

        Pass :data:`None` to remove the URL.

        :param url: The URL to use.
        :type url: str | None
        :return: The resulting embed.
        :rtype: :class:`Embed2`
        """
        author = attr.evolve(self.author, url=url)
        return attr.evolve(self, author=author)

    def __len__(self) -> int:
        return sum([
            len(self.title), len(self.description),
            sum(len(f) for f in self.fields),
            len(self.footer), len(self.author),
        ])
