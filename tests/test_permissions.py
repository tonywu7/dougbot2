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
from discord import Permissions
from duckcord.permissions import Permissions2

v1 = 0b01001110
v2 = 0b11100101
v3 = 0b11101110
v4 = 0b11111111
v5 = 0b01110110

v1_sub_v2 = 0b00001010
v2_sub_v1 = 0b10100001

v1_xor_v2 = 0b10101011
v3_xor_v4 = 0b00010001

not_v1 = 0b111111111111111111111111110110001


def p1():
    return Permissions2(v1)


def p2():
    return Permissions2(v2)


def p3():
    return Permissions2(v3)


def p4():
    return Permissions2(v4)


def p5():
    return Permissions2(v5)


def test_init_value():
    assert p1().value == v1


def test_init_kwargs():
    assert Permissions2(administrator=True, speak=False).value == (1 << 3)


def test_casting():
    assert int(p1()) == v1
    assert int(p2()) != v1


def test_hashing():
    p = p1()
    v = v1
    d1 = {p: True}
    d2 = {v: True}
    assert p in d1
    assert p not in d2
    assert v not in d1
    assert v in d2


def test_equality():
    assert p1() == p1()


def test_equality_compat():
    assert p1() == Permissions(v1)


def test_le():
    assert p1() <= p3()
    assert p1() <= p1()


def test_ge():
    assert p4() >= p2()
    assert p2() >= p2()


def test_lt():
    assert p1() < p3()
    with pytest.raises(AssertionError):
        assert p1() < p1()


def test_gt():
    assert p4() > p3()
    with pytest.raises(AssertionError):
        assert p4() < p4()


def test_immutability_1():
    with pytest.raises(NotImplementedError):
        p1().add_reactions = True


def test_immutability_2():
    p = Permissions2.text()
    p_ = p.evolve(send_messages=False)
    assert p_ is not None
    assert p_.send_messages is False
    assert p.send_messages is True


def test_and():
    assert (p1() & p2()).value == v1 & v2


def test_or():
    assert (p1() | p2()).value == v1 | v2


def test_sub():
    s1 = p1() - p2()
    s2 = p2() - p1()
    assert s1.value == v1_sub_v2
    assert s2.value == v2_sub_v1


def test_xor():
    x1 = p1() ^ p2()
    x2 = p3() ^ p4()
    assert x1.value == v1_xor_v2
    assert x2.value == v3_xor_v4


def test_xor_2():
    assert (p1() ^ p2() ^ p2()) == p1()


def test_invert():
    assert (~p1()).value == not_v1


def test_invert_2():
    assert ~~p1() == p1()


def test_isdisjoint():
    assert Permissions2(0b11100010).isdisjoint(Permissions2(0b00011101))


def test_union():
    assert p4() == p1().union(p2(), p5())


def test_intersection():
    assert Permissions2(0b01000100) == p1().intersection(p2(), p5())


def test_difference():
    assert Permissions2.none() == p4().difference(p1(), p2(), p5())
