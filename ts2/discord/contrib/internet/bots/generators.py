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

from typing import Optional

from discord import Message, MessageReference
from discord.ext.commands import command

from ts2.discord.context import Circumstances
from ts2.discord.ext.common import doc
from ts2.discord.ext.services.rand import FakerLocales, get_faker
from ts2.discord.utils.common import a, trunc_for_field
from ts2.discord.utils.markdown import spongebob


class ContentGenerationCommands:
    @command('lipsum', aliases=('lorem',))
    @doc.description(
        f'{a("Lorem ipsum", "https://www.lipsum.com/")} dolor sit amet: '
        'generate random text.',
    )
    @doc.argument('language', 'The language in which the text should be generated.')
    @doc.invocation((), 'Generate a paragraph.')
    @doc.invocation(('language',), 'Generate a paragraph in one of the supported languages.')
    async def lipsum(self, ctx: Circumstances, language: Optional[FakerLocales] = 'la'):
        fake = get_faker(language)
        sentences = fake.sentences(5)
        if language == 'la':
            sentences = ['Lorem ipsum dolor sit amet, consectetur adipiscing elit.', *sentences]
        return await ctx.response(ctx, content=' '.join(sentences)).deleter().run()

    @command('spongebob', aliases=('mock',))
    @doc.description('uSELesS FeATure.')
    @doc.argument('content', 'The text to transform.')
    @doc.argument('message', 'The message whose text content to transform.')
    @doc.accepts_reply('Use the text content of the replied-to message.')
    @doc.use_syntax_whitelist
    @doc.invocation(('content',), None)
    @doc.invocation(('message',), None)
    @doc.invocation(('reply',), None)
    async def mock(
        self, ctx: Circumstances,
        message: Optional[Message],
        *, content: Optional[str] = '',
        reply: Optional[MessageReference] = None,
        threshold: Optional[float] = .5,
    ):
        if not content:
            if message:
                content = message.content
            elif reply:
                ref = reply.resolved
                if ref:
                    content = ref.content
        if not content:
            as_error = True
            if not message and not reply:
                content = "There's nothing to convert"
            else:
                content = 'That message has no text in it'
        else:
            as_error = False
        await ctx.trigger_typing()
        res, has_alpha = spongebob(content, threshold)
        res = trunc_for_field(res, 1920)
        if as_error:
            raise doc.NotAcceptable(res)
        if reply:
            reference = reply
        elif message:
            reference = message.to_reference()
        else:
            reference = ctx.message.to_reference()
        await ctx.response(ctx, content=res, reference=reference).deleter().run()
        if not has_alpha:
            err = "There wasn't any letter to change"
            res, *args = spongebob(err, threshold)
            raise doc.NotAcceptable(res)
