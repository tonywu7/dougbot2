duckcord.py
===========

   |discord.py|_ **dataclasses but with more duck-typing.**

   .. |discord.py| replace:: **discord.py**
   .. _discord.py: https://discordpy.readthedocs.io/

This module provides alternative implementations of several discord.py
dataclasses, fixing some pitfalls and providing a few convenience methods.

The most significant difference between these implementations and their original
counterparts is that all of them are meant to be **immutable**: attempts to
update their values will either raise :class:`NotImplementedError` or return a
new instance instead, leaving the original object unchanged.

None are fully drop-in replacements for discord.py classes, although they
expose the same interfaces.

.. note::

   True immutability is impossible in Python.


.. toctree::
   :maxdepth: 2
   :caption: Contents:


Color
=====

.. autoclass:: duckcord.color.Color2

.. py:function:: int()
   :noindex:
.. automethod:: duckcord.color.Color2.__index__

.. py:function:: hash()
   :noindex:
.. automethod:: duckcord.color.Color2.__hash__

.. py:function:: operator==
.. automethod:: duckcord.color.Color2.__eq__
.. py:function:: operator!=
.. automethod:: duckcord.color.Color2.__ne__

Permissions
===========

.. autoclass:: duckcord.permissions.Permissions2

.. py:function:: int()
   :noindex:
.. automethod:: duckcord.permissions.Permissions2.__index__

.. py:function:: hash()
   :noindex:
.. automethod:: duckcord.permissions.Permissions2.__hash__

.. py:function:: Permissions2.update(**kwargs) -> Permissions2
.. automethod:: duckcord.permissions.Permissions2.evolve(**kwargs) -> Permissions2

.. automethod:: duckcord.permissions.Permissions2.devolve(**kwargs) -> Permissions2

.. py:function:: operator==
.. automethod:: duckcord.permissions.Permissions2.__eq__
.. py:function:: operator=!
.. automethod:: duckcord.permissions.Permissions2.__ne__

.. note::
   **The following operators** ``<`` ``>`` ``<=`` **and** ``>=`` **return**
   :data:`NotImplemented` **for unsupported types instead of raising**
   :exc:`TypeError`.

   If the other operand implements comparison with :class:`Permissions2`, Python
   will use the value returned from the reflected operator method. Otherwise
   a :exc:`TypeError` is still raised.

   See :meth:`object.__lt__` for more info.

.. py:function:: operator<
.. py:function:: Permissions2.is_strict_subset(other)
.. automethod:: duckcord.permissions.Permissions2.__lt__
.. py:function:: operator>
.. py:function:: Permissions2.is_strict_superset(other)
.. automethod:: duckcord.permissions.Permissions2.__gt__
.. py:function:: operator<=
.. py:function:: Permissions2.issubset(other)
.. py:function:: Permissions2.is_subset(other)
.. automethod:: duckcord.permissions.Permissions2.__le__
.. py:function:: operator>=
.. py:function:: Permissions2.issuperset(other)
.. py:function:: Permissions2.is_superset(other)
.. automethod:: duckcord.permissions.Permissions2.__ge__

.. note::
   **The following operators** ``&`` ``|`` ``-`` and ``^`` **return**
   :data:`NotImplemented` **for unsupported types instead of raising**
   :exc:`TypeError`.

   If the other operand implements comparison with :class:`Permissions2`, Python
   will use the value returned from the reflected operator method. Otherwise
   a :exc:`TypeError` is still raised. ``__rand__`` ``__ror__`` ``__rsub__`` and
   ``__rxor__`` are aliased to ``__and__`` ``__or__`` ``__sub__`` and
   ``__xor__``, thus for mixed-typed expressions the :class:`Permissions2`
   object does not have to be the left operand.

   See :meth:`object.__add__` for more info.

.. py:function:: operator&
.. py:function:: Permissions2.intersection(*others)
.. automethod:: duckcord.permissions.Permissions2.__and__

.. py:function:: operator|
.. py:function:: Permissions2.union(*others)
.. automethod:: duckcord.permissions.Permissions2.__or__

.. py:function:: operator-
.. py:function:: Permissions2.difference(*others)
.. automethod:: duckcord.permissions.Permissions2.__sub__

.. py:function:: operator^
.. py:function:: Permissions2.symmetric_difference(other)
.. automethod:: duckcord.permissions.Permissions2.__xor__

.. py:function:: operator~
.. automethod:: duckcord.permissions.Permissions2.__invert__

.. automethod:: duckcord.permissions.Permissions2.isdisjoint

.. py:function:: operator@
.. automethod:: duckcord.permissions.Permissions2.__matmul__(other: PermissionOverride) -> Permissions2

Permission override
===================

.. autoclass:: duckcord.permissions.PermissionOverride
.. autoproperty:: duckcord.permissions.PermissionOverride.allowed
.. autoproperty:: duckcord.permissions.PermissionOverride.denied

.. py:function:: PermissionOverride.update(**kwargs: bool) -> PermissionOverride
.. automethod:: duckcord.permissions.PermissionOverride.evolve(**kwargs) -> PermissionOverride

.. automethod:: duckcord.permissions.PermissionOverride.devolve(**kwargs) -> PermissionOverwrite

.. py:function:: operator|
.. automethod:: duckcord.permissions.PermissionOverride.__or__(other)

.. py:function:: operator@
.. automethod:: duckcord.permissions.PermissionOverride.__matmul__(other)

Embed
=====

.. warning::
   Requires `attrs <https://www.attrs.org/en/stable/>`_.

.. autoclass:: duckcord.embeds.Embed2
.. automethod:: duckcord.embeds.Embed2.convert_embed
.. automethod:: duckcord.embeds.Embed2.from_dict
.. automethod:: duckcord.embeds.Embed2.to_dict
.. automethod:: duckcord.embeds.Embed2.copy

.. automethod:: duckcord.embeds.Embed2.use_as_author
.. automethod:: duckcord.embeds.Embed2.use_member_color
.. automethod:: duckcord.embeds.Embed2.personalized

.. automethod:: duckcord.embeds.Embed2.add_field
.. automethod:: duckcord.embeds.Embed2.insert_field_at
.. automethod:: duckcord.embeds.Embed2.set_field_at
.. automethod:: duckcord.embeds.Embed2.clear_fields
.. automethod:: duckcord.embeds.Embed2.set_timestamp
.. automethod:: duckcord.embeds.Embed2.set_author
.. automethod:: duckcord.embeds.Embed2.remove_author
.. automethod:: duckcord.embeds.Embed2.set_footer

.. py:function:: duckcord.embeds.Embed2.set_image
.. py:function:: duckcord.embeds.Embed2.set_thumbnail
.. py:function:: duckcord.embeds.Embed2.set_color
.. py:function:: duckcord.embeds.Embed2.set_title
.. py:function:: duckcord.embeds.Embed2.set_description
.. py:function:: duckcord.embeds.Embed2.set_url

   Functions to set embed attributes.

   Pass :data:`None` to remove the attribute.

   :return: The resulting embed.
   :rtype: :class:`Embed2`
