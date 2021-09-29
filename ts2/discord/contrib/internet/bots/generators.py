# generators.py
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
from typing import Literal, Optional

from discord.ext.commands import command
from faker import Faker

from ts2.discord.context import Circumstances
from ts2.discord.ext.common import Choice, doc
from ts2.discord.utils.common import a

fake: Faker = None

LOCALES = OrderedDict([
    ('en-US', 1.0),
    ('zh-CN', 1.0),
    ('fr-FR', 0.8),
    ('ja-JP', 0.7),
    ('pl-PL', 0.7),
    ('la', 0.3),
])

FakerLocales = Choice[[*LOCALES.keys()], Literal['language code']]


def get_faker(locale: str = 'en-US') -> Faker:
    """Get the program's global Faker instance."""
    global fake
    if not fake:
        fake = Faker(LOCALES)
    return fake[locale]


class ContentGenerationCommands:
    """Commands (mixin) for generating arbitrary/random responses."""

    @command('lipsum', aliases=('lorem',))
    @doc.description(
        f'{a("Lorem ipsum", "https://www.lipsum.com/")} dolor sit amet: '
        'generate random text.',
    )
    @doc.argument('language', 'The language in which the text should be generated.')
    @doc.invocation((), 'Generate a paragraph.')
    @doc.invocation(('language',), 'Generate a paragraph in one of the supported languages.')
    async def lipsum(self, ctx: Circumstances, language: Optional[FakerLocales] = 'la'):
        """Create text using Faker's lorem provider."""
        fake = get_faker(language)
        sentences = fake.sentences(5)
        if language == 'la':
            sentences = ['Lorem ipsum dolor sit amet, consectetur adipiscing elit.', *sentences]
        return await ctx.response(ctx, content=' '.join(sentences)).deleter().run()
