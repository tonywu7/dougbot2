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

from functools import reduce
from operator import and_, or_
from typing import Optional

from discord import Guild, Member, PermissionOverwrite, Permissions, Role
from discord.abc import GuildChannel
from discord.flags import flag_value
from discord.permissions import permission_alias


class Permissions2(Permissions):
    """Inherits from and replaces :class:`discord.Permissions`.

    Supports casting to :class:`int`.

    Supports the following operators:

    * **Equality testing:** ``==`` ``!=``
    * **Set comparison:** ``<=`` subset, ``>=`` superset, ``<`` strict subset,
      ``>`` strict superset
    * **Set algebra:** ``&`` intersection, ``|`` union, ``-`` difference, ``^``
      symmetric difference, ``~`` inversion
    * **Matrix multiplication:** ``@`` for operating with
      :class:`PermissionOverride`

    .. warning::
        :class:`Permissions2` objects are **immutable**. Attempting to set
        individual permission attributes raises :exc:`NotImplementedError`.

        To get a :class:`Permissions2` object from another one with some
        settings changed, use :meth:`evolve`.

        **Not a drop-in replacement.** To get a :class:`discord.Permissions`
        object, use :meth:`downgrade`.
    """

    VALID_FLAGS: dict[str, int]
    DEFAULT_VALUE: int

    __slots__ = ()

    def __init__(self, permissions: int = 0, **kwargs: bool):
        """Create a :class:`Permissions2` object.

        .. note::
            :class:`Permissions2` **accepts any object that can be cast to an**
            :class:`int`, **which includes** :class:`Permissions2` **itself.**

            This means it is safe to pass a :class:`Permissions2` object to the
            constructor: ``Permissions2(Permissions2(0))`` returns a new
            ``Permissions2(0)`` object instead of throwing an exception.
        """
        self.value = int(permissions)
        for flag in kwargs.items():
            self.value = self._set_bit(self.value, flag, True)

    def _set_flag(self, o, toggle: bool):
        name = type(self).__name__
        raise NotImplementedError(
            f'{name} objects are immutable,'
            f' use {name}.evolve() instead.',
        )

    def __index__(self):
        """Return the underlying ``value`` as an :class:`int`."""
        return self.value

    __int__ = __index__

    def __bool__(self) -> bool:
        """Return :data:`True` if this permission allows anything."""
        return bool(self.value)

    def __hash__(self):
        """Return a hash for this :class:`Permissions2`.

        Returns ``hash((type(self), self.value, 37))``.

        .. note::
            In discord.py's implementation of :class:`discord.Permissions`
            (as of v1.7.3), for a ``Permissions p``, ``hash(p)`` returns
            ``hash(p.value)``, which means **the hash of a**
            :class:`discord.Permissions` **object will collide
            with the hash of its underlying value:**

            Both ``0`` and ``Permissions(0)`` can still coexist in a
            :class:`dict`, however, to ensure that they can coexist,
            Python must resolve the collision by calling
            :meth:`__eq__` to determine that they are not equal.

            This function avoids such a pitfall by including the type object in
            hash calculation.
        """
        return hash((type(self), self.value, 37))

    def __iter__(self):
        """Return an iterator yielding names of individual permissions this\
            :class:`discord.Permissions` object has.

        To get a list of permission names this object doesn't have, iterate
        over its complement.
        """
        cls = type(self)
        for f in self.VALID_FLAGS:
            if isinstance(getattr(cls, f), permission_alias):
                continue
            if getattr(self, f) is True:
                yield f

    def evolve(self, **kwargs: bool) -> Permissions2:
        """Return a new :class:`Permissions2` object with values updated\
            according to ``kwargs``.

        This :class:`Permissions2` object remains unchanged.

        :param \\**kwargs: Permission names to update.
        :type \\**kwargs: :class:`bool`
        """
        # Permissions objects should be immutable because they are hashable.
        # Incurs a slight overhead because of object initialization.
        return type(self)(reduce(self._set_bit, kwargs.items(), self.value))

    update = evolve

    def __eq__(self, other):
        """Return :data:`True` if the other :class:`Permissions2` has the same\
        permissions value as this one.

        Implements the ``==`` operator.

        .. note::
            :class:`Permissions2` will test equal against all of its subclasses
            and :class:`discord.Permissions` as long as the underlying values
            are equal, and will test unequal against all
            non-:class:`Permissions` objects.
        """
        if not isinstance(other, Permissions):
            return NotImplemented
        return self.value == other.value

    def __ne__(self, other):
        """Return :data:`True` if the other :class:`Permissions2` has different\
        permissions than this one.

        Implements the ``!=`` operator.
        """
        if not isinstance(other, Permissions):
            return NotImplemented
        return self.value != other.value

    def __le__(self, other):
        """Return :data:`True` if this :class:`Permissions2` is a subset of
        another :class:`Permissions2`.

        Implements the ``<=`` operator.
        """
        if not isinstance(other, Permissions):
            return NotImplemented
        return (self.value & other.value) == self.value

    def __ge__(self, other):
        """Return :data:`True` if this :class:`Permissions2` is a superset of
        another :class:`Permissions2`.

        Implements the ``>=`` operator.
        """
        if not isinstance(other, Permissions):
            return NotImplemented
        return (self.value | other.value) == self.value

    def __lt__(self, other):
        """Return :data:`True` if this :class:`Permissions2` is a *strict
        subset* of another :class:`Permissions2`.

        Implements the ``<`` operator.
        """
        # It would be better to only define __lt__ and __eq__
        # and have functools.total_ordering take care of the rest.
        if not isinstance(other, Permissions):
            return NotImplemented
        # Evaluating NotImplemented as bool is deprecated since 3.9
        return (self.value != other.value
                and (self.value & other.value) == self.value)

    def __gt__(self, other):
        """Return :data:`True` if this :class:`Permissions2` is a *strict
        superset* of another :class:`Permissions2`.

        Implements the ``>`` operator.
        """
        if not isinstance(other, Permissions):
            return NotImplemented
        return (self.value != other.value
                and (self.value | other.value) == self.value)

    issubset = is_subset = __le__
    issuperset = is_superset = __ge__
    is_strict_subset = __lt__
    is_strict_superset = __gt__

    @classmethod
    def _set_bit(cls, value: int, flag: tuple[str, bool], strict: bool = False):
        flag_name, is_set = flag
        flag_value = cls.VALID_FLAGS.get(flag_name)
        if flag_value is None:
            if strict:
                raise TypeError(f'{flag_name} is not a valid permission name.')
            return value
        if is_set:
            return value | flag_value
        return value & ~flag_value

    def __and__(self, other):
        """Return the common permissions of the two :class:`Permissions2`\
            object.

        Implements the ``&`` operator.

        This allows :class:`Permissions2` to directly participate in
        calculations (instead of having to first retrieve their ``value``
        attributes):

        >>> Permissions2(1) & Permissions2(128)
        ... <Permissions2 value=1>
        """
        try:
            return type(self)(self.value & int(other))
        except TypeError:
            return NotImplemented

    def __or__(self, other):
        """Return the combined permissions of the two :class:`Permissions2`\
            object.

        Implements the ``|`` operator.

        This allows :class:`Permissions2` to directly participate in
        calculations:

        >>> Permissions2(1) | Permissions2(128)
        ... <Permissions2 value=129>

        .. note::
            This also makes it easier to work with a series of
            :class:`Permissions2` objects, e.g. to calculate the total
            permissions of a member with :func:`functools.reduce`:

            >>> from functools import reduce
            >>> from operator import or_
            >>> perms = []
            >>> perms.append(Permissions2(read_message_history=True))
            >>> perms.append(Permissions2(send_messages=True))
            >>> perms.append(Permissions2(manage_messages=True))
            >>> reduce(or_, perms, Permissions2.none())
            ... <Permissions2 value=75776>
        """
        try:
            return type(self)(self.value | int(other))
        except TypeError:
            return NotImplemented

    def __sub__(self, other):
        """Return the set of permissions in this :class:`Permissions2` object\
        but not in the other one.

        Implements the ``-`` operator.
        """
        try:
            return type(self)(self.value & ~int(other))
        except TypeError:
            return NotImplemented

    def __xor__(self, other):
        """Return the set of permissions in either :class:`Permissions2` object\
        but not in both.

        Implements the ``^`` operator.
        """
        try:
            return type(self)(self.value ^ int(other))
        except TypeError:
            return NotImplemented

    def __invert__(self):
        """Return the complement of this set of permissions.

        Relies on :meth:`discord.Permissions.all` to return the value for a
        full set of permissions. Implements the ``~`` unary operator.
        """
        return type(self)(self.all() & ~self.value)

    __rand__ = __and__
    __ror__ = __or__
    __rsub__ = __sub__
    __rxor__ = __xor__

    def isdisjoint(self, other):
        """Return :data:`True` if this and the other :class:`Permissions2`\
        allow entirely different perms."""
        return (self.value & int(other)) == 0

    def union(self, *others: Permissions2) -> Permissions2:
        return type(self)(reduce(or_, [p.value for p in others], self.value))

    def intersection(self, *others: Permissions2) -> Permissions2:
        return type(self)(reduce(and_, [p.value for p in others], self.value))

    def difference(self, *others: Permissions2) -> Permissions2:
        all_ = self.all().value
        return type(self)(reduce(and_, [all_ & ~p.value for p in others],
                                 self.value))

    def symmetric_difference(self, other: Permissions2) -> Permissions2:
        v = self ^ other
        if v is NotImplemented:
            raise TypeError((
                'symmetric_difference unsupported'
                f' between {type(self)} and {type(other)}'
            ))
        return v

    def downgrade(self) -> Permissions:
        """Return an original :class:`discord.Permissions` object with the same\
            settings."""
        return Permissions(self.value)

    def handle_overwrite(self, allow: int, deny: int):
        return type(self)((self.value & ~deny) | allow)

    def __matmul__(self, other: PermissionOverride) -> Permissions2:
        """Return a new :class:`Permissions2` object with the\
            :class:`PermissionOverride` applied.

        Implements the ``@`` matrix-multiplication operator
        `(PEP 465) <https://www.python.org/dev/peps/pep-0465/>`_.

        >>> base = Permissions2.text()
        >>> override = PermissionOverride(send_messages=False)
        >>> result = base @ override
        >>> result.add_reactions
        ... True
        >>> result.send_messages
        ... False

        .. warning::
            ``@`` is not commutative. Left operand must be a
            :class:`Permissions2` object and right operand must be a
            :class:`PermissionOverride` object. ``__rmatmul__`` is not defined.
        """
        if not isinstance(other, PermissionOverride):
            return NotImplemented
        base = self.value
        allowed = other._allowed
        denied = other._denied
        return Permissions2((base | allowed) & ~denied)


class PermissionOverride(PermissionOverwrite):
    """Inherits from and replaces :class:`discord.PermissionOverwrite`.

    Supports the following operators:

    1. ``==`` ``!=`` for equality testing
    2. ``|`` ``@`` for combining multiple :class:`PermissionOverride` objects

    .. warning::
        :class:`PermissionOverride` objects are **immutable**. Attempting to set
        individual permission attributes raises :exc:`NotImplementedError`.

        To get a :class:`PermissionOverride` object from another one with some
        settings changed, use :meth:`evolve`.

        **Not a drop-in replacement.** To get a
        :class:`discord.PermissionOverwrite` object, use :meth:`downgrade`.
    """

    __slots__ = ('_allowed', '_denied')

    VALID_NAMES: set[str]
    PURE_FLAGS: set[str]

    class _Delegate(Permissions2):
        """Compat object for flag attribute getters."""

        __slots__ = ('parent',)

        def __init__(self, parent: PermissionOverride):
            self.parent = parent

        def get(self, key: str):
            cls = type(self)
            flag: flag_value = getattr(cls, key)
            bit = flag.flag
            allowed = self.parent._allowed & bit
            if allowed:
                return True
            denied = self.parent._denied & bit
            if denied:
                return False
            return None

        def __eq__(self, other: dict[str, bool] | PermissionOverride._Delegate):
            if isinstance(other, type(self)):
                return (self.parent._allowed == other.parent._allowed
                        and self.parent._denied == other.parent._denied)
            elif isinstance(other, dict):
                # Support comparing with the original
                # PermissionOverwrite objects
                other_allowed, other_denied = self.parent._dict_to_bits(other)
                return (self.parent._allowed == other_allowed
                        and self.parent._denied == other_denied)
            else:
                return NotImplemented

    _values: _Delegate

    @classmethod
    def _dict_to_bits(cls, flags: dict[str, bool],
                      strict: bool = True) -> tuple[int, int]:
        _allowed: int = 0
        _denied: int = 0
        for k, v in flags.items():
            if k not in cls.VALID_NAMES:
                if strict:
                    raise TypeError(f'{k} is not a valid permission name.')
                else:
                    continue
            if v is None:
                continue
            flag: flag_value = getattr(cls._Delegate, k)
            bit = flag.flag
            if v:
                _allowed |= bit
            else:
                _denied |= bit
        return _allowed, _denied

    def __repr__(self):
        return '<%s allow=%s deny=%s>' % (
            type(self).__name__, self._allowed, self._denied,
        )

    def __new__(cls, **kwargs):
        obj = super().__new__(cls)
        obj._values = cls._Delegate(obj)
        return obj

    def __init__(self, **kwargs: bool | None):
        # Since we intend PermissionOverride to be immutable
        # there's no point in using a dict to store flags
        # and create a Permissions object every time
        # .allowed or .denied is accessed.
        self._allowed, self._denied = self._dict_to_bits(kwargs)

    def __eq__(self, other):
        if not isinstance(other, PermissionOverwrite):
            return NotImplemented
        return self._values == other._values

    def __hash__(self):
        return hash((type(self), self._allowed, self._denied, 37))

    def __bool__(self) -> bool:
        return not self.is_empty()

    def _set(self, key, value):
        name = type(self).__name__
        raise NotImplementedError(
            f'{name} objects are immutable,'
            f' use {name}.evolve() instead.',
        )

    @property
    def allowed(self) -> Permissions2:
        """Get the permissions allowed by this override as a\
            :class:`Permissions2` object."""
        return Permissions2(self._allowed)

    @property
    def denied(self) -> Permissions2:
        """Get the permissions denied by this override as a\
            :class:`Permissions2` object."""
        return Permissions2(self._denied)

    def pair(self) -> tuple[Permissions2, Permissions2]:
        return self.allowed, self.denied

    @classmethod
    def _from_values(cls, allow: int = 0, deny: int = 0):
        instance = cls()
        instance._allowed = int(allow)
        instance._denied = int(deny)
        return instance

    @classmethod
    def _from_original(cls, overwrite: PermissionOverwrite):
        return cls(**overwrite._values)

    @classmethod
    def from_pair(cls, allow: Permissions, deny: Permissions):
        allow = Permissions2(allow.value)
        deny = Permissions2(deny.value)
        # Remove duplicate settings with allow taking precedence over deny
        deny -= allow
        return cls._from_values(allow.value, deny.value)

    def is_empty(self) -> bool:
        """Return :data:`True` if this override explicitly allows/denies anything."""
        return self._allowed == 0 and self._denied == 0

    def evolve(self, **kwargs: bool | None) -> PermissionOverride:
        """Return a new :class:`PermissionOverride` object with values updated\
            according to ``kwargs``.

        This :class:`PermissionOverride` object remains unchanged.

        :param \\**kwargs: Permission names to update.
        :type \\**kwargs: :class:`bool` | :data:`None`
        """
        allowed = self._allowed
        denied = self._denied
        for k, v in kwargs.items():
            flag: flag_value | None = getattr(self._Delegate, k)
            if flag is None:
                continue
            bit = flag.flag
            if v is True:
                allowed |= bit
                denied &= ~bit
            elif v is False:
                allowed &= ~bit
                denied |= bit
            else:
                allowed &= ~bit
                denied &= ~bit
        return self._from_values(allowed, denied)

    update = evolve

    def __or__(self, other: PermissionOverwrite) -> PermissionOverride:
        """Simulate Discord's calculation for overwrites on the same hierarchy\
            level.

        Implements the ``|`` operator.

        The calculation rules are as follows:

        - If either operand allows a permission, the resulting override allows
          this permission.
        - If one of the operand denies a permission and the other does not allow
          (deny or passthrough) the same permission, the resulting override
          explicitly denies this permission.
        - For all other permissions, the resulting override neither allows
          nor denies them (set to :data:`None`).
        """
        if isinstance(other, type(self)):
            other_allowed, other_denied = other._allowed, other._denied
        elif isinstance(other, PermissionOverwrite):
            other_allowed, other_denied = self._dict_to_bits(other._values)
        else:
            return NotImplemented
        allowed = self._allowed | other_allowed
        denied = (self._denied | other_denied) & ~allowed
        return self._from_values(allowed, denied)

    def __matmul__(self, other: PermissionOverride) -> PermissionOverride:
        """Simulate Discord's calculation for overwrites on different\
            hierarchies.

        Implements the ``@`` matrix multiplication operator
        `(PEP 465) <https://www.python.org/dev/peps/pep-0465/>`_.
        Note that ``@`` is not commutative.

        The right operand is the overwrite with a higher precedence over the
        left operand. The calculation rules are as follows: for each perm:

        - If the right operand allows or denies it, the resulting override
          allows or denies it.
        - Otherwise, the setting for this perm is the same as the setting
          defined on the left operand.

        .. note::
            A mnemonic for which operand has a higher priority is that ``@``
            stands for "at this channel" (channel override) or "@this member"
            (member override).

        .. note::
            Together with :meth:`__or__` and :meth:`Permissions2.__matmul__`,
            this operator allows for simulating Discord's permission calculation
            in any context, without having to rely on :class:`discord.Role`
            or :class:`discord.Member` objects.

            >>> # Server-wide permissions
            >>> server = Permissions2(...)
            >>> # Permissions for @everyone in a channel
            >>> perm_here = PermissionsOverride(...)
            >>> # Overrides associated with a member's roles in this channel
            >>> perm_role1 = PermissionsOverride(...)
            >>> perm_role2 = PermissionsOverride(...)
            >>> # Override for this member in this channel
            >>> perm_member = PermissionsOverride(...)
            >>> # Total permissions for this member in this channel
            >>> server @ perm_here @ (perm_role1 | perm_role2) @ perm_member
        """
        if not isinstance(other, type(self)):
            return NotImplemented
        denied = (self._denied | other._denied) & ~other._allowed
        allowed = (self._allowed | other._allowed) & ~other._denied
        return self._from_values(allowed, denied)

    @classmethod
    def upgrade(cls, override: PermissionOverwrite) -> PermissionOverride:
        return cls.from_pair(*override.pair())

    def downgrade(self) -> PermissionOverwrite:
        """Return an original :class:`discord.PermissionOverwrite` object with the\
            same settings."""
        return PermissionOverwrite.from_pair(*self.pair)


def get_total_perms(
    *roles: Role, channel: Optional[GuildChannel] = None,
    member: Optional[Member] = None,
) -> Permissions2:
    """Calculate the total permissions for a set of roles, optionally in a\
        channel.

    :param \\*roles: The roles whose permissions will be in effect
    :type \\*roles: :class:`discord.Role`
    :param channel: The channel whose overrides will apply, defaults to None
    :type channel: :class:`discord.abc.GuildChannel`, optional
    :param member: The member whose override will apply, defaults to None
    :type member: :class:`discord.Member`, optional
    :return: The final set of permissions
    :rtype: :class:`Permissions2`
    """
    roles = set(roles)
    perms = [Permissions2(r.permissions.value) for r in roles]
    if any(p.administrator for p in perms):
        return Permissions2.all()
    combined: Permissions2 = reduce(or_, perms, Permissions2(0))
    if not channel:
        return combined
    guild: Guild = channel.guild
    everyone = guild.default_role
    roles.discard(everyone)
    overrides = {r: PermissionOverride.upgrade(o)
                 for r, o in channel.overwrites.items()}
    here = overrides.get(everyone, PermissionOverride())
    applied = [overrides.get(r, PermissionOverride()) for r in roles]
    override: PermissionOverride = reduce(or_, applied, PermissionOverride())
    combined = combined @ here @ override
    override2 = overrides.get(member)
    if override2:
        combined @= override2
    return combined
