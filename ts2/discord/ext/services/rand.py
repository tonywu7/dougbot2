# rand.py
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

from collections import OrderedDict

from faker import Faker

from ..common import Choice

fake: Faker = None

LOCALES = OrderedDict([
    ('en-US', 1.0),
    ('zh-CN', 1.0),
    ('fr-FR', 0.8),
    ('ja-JP', 0.7),
    ('pl-PL', 0.7),
    ('la', 0.3),
])

FakerLocales = Choice[[*LOCALES.keys()], 'language code']


def get_faker(locale: str = 'en-US') -> Faker:
    global fake
    if not fake:
        fake = Faker(LOCALES)
    return fake[locale]
