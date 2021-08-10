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

import pytest
from duckcord.permissions import PermissionOverride, Permissions2


def p1():
    return PermissionOverride(
        add_reactions=True,
        manage_roles=True,
        read_message_history=True,
    )


def p2():
    return PermissionOverride(
        send_messages=True,
        manage_roles=False,
    )


def p3():
    return PermissionOverride._from_values(Permissions2.all())


def p4():
    return PermissionOverride._from_values(Permissions2.voice())


def p5():
    return PermissionOverride._from_values(Permissions2.text())


def p6():
    return PermissionOverride._from_values(0, Permissions2.text())


def assert_disjoint(p: PermissionOverride):
    print(f'{p._allowed:>032b}')
    print(f'{p._denied:>032b}')
    assert (p._allowed & p._denied) == 0


def test_init():
    p1()


def test_getter():
    p = p2()
    assert p.send_messages is True
    assert p.manage_roles is False
    assert p.read_message_history is None


def test_equality():
    assert p1() == p1()


def test_immutability_1():
    with pytest.raises(NotImplementedError):
        p1().add_reactions = True


def test_immutability_2():
    p = p4()
    p_ = p.update(send_messages=False)
    assert p_ is not None
    assert p._allowed == Permissions2.voice().value
    assert p_.send_messages is False
    assert p_.speak is True
    assert p_.administrator is None


def test_empty():
    assert PermissionOverride._from_values().is_empty()


def test_empty_2():
    p = p1()
    p_a = p.evolve(add_reactions=False)
    p_b = p.evolve(add_reactions=None, manage_roles=None)
    p_c = p.evolve(
        add_reactions=None,
        manage_roles=None,
        read_message_history=None,
    )

    assert not p_a.is_empty()
    assert not p_b.is_empty()
    assert p_c.is_empty()


def test_or():
    p = p1() | p2() | p4() | p6()
    assert_disjoint(p)
    assert p.administrator is None
    assert p.add_reactions is True
    assert p.manage_roles is True
    assert p.speak is True
    assert p.send_messages is True
    assert p.embed_links is False
    assert p.use_slash_commands is False


def test_matmul():
    p = p5() @ p6() @ p2()
    assert_disjoint(p)
    assert p.administrator is None
    assert p.send_messages is True
    assert p.add_reactions is False
    assert p.manage_roles is False
