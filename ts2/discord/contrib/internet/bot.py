# bot.py
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

from datetime import datetime
from typing import Literal, Optional, Union

import aiohttp
import pytz
from discord import Member, Message, MessageReference, Role
from discord.ext.commands import BucketType, Greedy, command

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext.common import Maybe, RegExp, User, doc, lang
from ts2.discord.ext.services.datetime import Timezone
from ts2.discord.ext.services.oeis import OEIS
from ts2.discord.ext.services.rand import FakerLocales, get_faker
from ts2.discord.utils.common import Color2, Embed2, a, async_first, code, tag, trunc_for_field
from ts2.discord.utils.markdown import spongebob

from .models import RoleTimezone


class Internet(
    Gear, name='Internet', order=10,
    description='Not Google.',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('oeis')
    @doc.description('Lookup a sequence from [OEIS](https://oeis.org/) '
                     'by its integers or by its A-number.')
    @doc.argument('integers', 'The sequence of integers to lookup, separated by space only.')
    @doc.argument('a_number', 'The OEIS A-number to lookup.')
    @doc.invocation((), 'Get a sequence by searching for a random A-number (may not return results).')
    @doc.invocation(('integers',), 'Find a sequence matching these numbers.')
    @doc.invocation(('a_number',), 'Find the exact sequence with this A-number.')
    @doc.invocation(('integers', 'a_number'), False)
    @doc.example('1 1 2 3 5 8', 'Find the Fibonnacci numbers.')
    @doc.example('A018226', 'Find the magic numbers.')
    @doc.cooldown(1, 10, BucketType.guild)
    @doc.concurrent(1, BucketType.guild)
    async def oeis(self, ctx: Circumstances, integers: Greedy[int],
                   a_number: Optional[RegExp[Literal[r'[Aa]\d+', 'A-number', 'such as A0000045']]] = None):
        if integers:
            if len(integers) == 1:
                query = f'A{integers[0]}'
            else:
                query = ' '.join([str(n) for n in integers])
        elif a_number:
            query = a_number[0]
        else:
            query = None

        async with ctx.typing():
            try:
                oeis = OEIS(ctx.session)
                if query:
                    sequence, num_results = await oeis.get(query)
                else:
                    sequence, num_results = await oeis.random()
            except ValueError as e:
                reason = str(e)
                if not integers and not a_number:
                    reason = f'{reason} (Searched for a random A-number {query})'
                return await ctx.response(ctx, content=reason).timed(20).run()
            except aiohttp.ClientError:
                await ctx.reply('Network error while searching on OEIS')
                raise

        async def more_result(*args, **kwargs):
            await ctx.send(f'({num_results - 1} more {lang.pluralize(num_results - 1, "result")})')

        await (ctx.response(ctx, embed=sequence.to_embed())
               .callback(more_result).deleter().run(thread=True))

    @command('time')
    @doc.description('Get local time of a server member or a timezone.')
    @doc.argument('subject', 'The user/role/timezone whose local time to check')
    @doc.use_syntax_whitelist
    @doc.invocation((), 'Show your local time.')
    @doc.invocation(('subject',), (
        'Show the local time of a supported IANA timezone, or a user'
        ' if they have their timezone preference set,'
        ' or a server role, if it is associated with a timezone.'
    ))
    @Maybe.ensure
    async def time(
        self, ctx: Circumstances, *,
        subject: Maybe[Union[Timezone, Member, Role], None],
    ):
        timezone: Optional[pytz.BaseTzInfo] = None
        footer_fmt: str = 'Timezone: %(tz)s'
        TIMEZONE_NOT_SET = (
            '%(has_vp)s not set %(PRP_REFL)s a timezone preference'
            '\nnor assigned %(PRP_REFL)s a role timezone in the server.'
        )
        errors = subject.errors
        target = subject.value

        person: Optional[Member] = None
        role_ids: list[int] = []
        role_tz: Optional[RoleTimezone] = None
        if isinstance(target, pytz.BaseTzInfo):
            timezone = target
        elif isinstance(target, Role):
            role_ids = [target.id]
        elif isinstance(target, Member):
            person = target
            role_ids = [r.id for r in person.roles]
        else:
            person = ctx.author
            role_ids = [r.id for r in ctx.author.roles]

        if not timezone:
            if person:
                profile: User = await User.async_get(person)
                timezone = profile and profile.timezone

        if not timezone and role_ids:
            q = (RoleTimezone.objects.filter(role_id__in=role_ids)
                 .prefetch_related('role'))
            role_tz: Optional[RoleTimezone] = await async_first(q)
            timezone = role_tz and role_tz.timezone
            footer_fmt = 'Timezone: %(tz)s (from server role)'

        if not timezone:
            if not target:
                hint = (
                    'Set timezone preference with '
                    + ctx.format_command('my timezone')
                )
                msg = lang.address(TIMEZONE_NOT_SET, ctx.author, ctx, has='has')
                embed = (
                    Embed2(description=msg.capitalize())
                    .set_footer(text=hint)
                    .set_color(Color2.red())
                    .set_timestamp(None)
                )
                return await ctx.reply(embed=embed, delete_after=20)

            if isinstance(target, Member):
                msg = lang.address(TIMEZONE_NOT_SET, target, ctx, has='has')
                embed = (
                    Embed2(description=msg.capitalize())
                    .set_color(Color2.red())
                    .set_timestamp(None)
                )
                return await ctx.reply(embed=embed, delete_after=20)

            elif isinstance(target, Role):
                msg = f'{tag(target)} has no associated timezone.'
                embed = (
                    Embed2(description=msg)
                    .set_color(Color2.red())
                    .set_timestamp(None)
                )
                return await ctx.reply(embed=embed, delete_after=20)

            else:
                raise doc.NotAcceptable(
                    'Cannot find a timezone, user, or server role'
                    f' using {code(ctx.raw_input)}',
                )

        profile = await User.async_get(ctx.author)
        time = datetime.now(tz=timezone)
        formatted = profile.format_datetime(time)
        result = (
            Embed2(title='Local time', description=formatted)
            .set_footer(text=footer_fmt % {'tz': timezone})
            .set_timestamp(None)
        )
        if person:
            result = result.personalized(person)
        elif role_tz:
            result = result.set_color(role_tz.role.color)
        await ctx.reply(embed=result)
        if len(errors) == 3:
            error = (Embed2(description='\n'.join([str(e) for e in errors]))
                     .set_color(Color2.red()))
            await ctx.response(ctx, embed=error, delete_after=30).run()

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
                content = message
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
        await ctx.response(ctx, content=res).reply().deleter().run()
        if not has_alpha:
            err = "There wasn't any letter to change"
            res, *args = spongebob(err, threshold)
            raise doc.NotAcceptable(res)
