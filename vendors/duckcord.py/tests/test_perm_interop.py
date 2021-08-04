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


def test_matmul():
    base = Permissions2.text()
    override = PermissionOverride(send_messages=False)
    result = base @ override
    assert result.add_reactions is True
    assert result.send_messages is False


def test_matmul_commutative():
    base = Permissions2.text()
    override = PermissionOverride(send_messages=False)
    with pytest.raises(TypeError):
        override @ base


def test_calculator():
    base = Permissions2(view_channel=True, send_messages=True, add_reactions=True)
    here = PermissionOverride(send_messages=False, read_message_history=True)
    role_1 = PermissionOverride(view_channel=True, read_message_history=True)
    role_2 = PermissionOverride(send_messages=True, read_message_history=False,
                                use_external_emojis=True)
    role_3 = PermissionOverride(view_channel=True, send_messages=True, add_reactions=True,
                                read_message_history=True, use_external_emojis=False)

    member_1 = base @ here
    member_2 = base @ here @ role_1
    member_3 = base @ here @ role_2
    member_4 = base @ here @ (role_1 | role_2)
    member_5 = base @ here @ (role_1 | role_2 | role_3)
    member_6 = base @ here @ (role_1 | role_2) @ role_3

    assert member_1.view_channel
    assert member_1.read_message_history
    assert not member_1.send_messages

    assert member_2 == member_1

    assert member_3.send_messages
    assert member_3.use_external_emojis
    assert not member_3.read_message_history

    assert member_4.read_message_history

    assert member_5 == member_4

    assert not member_6.use_external_emojis
