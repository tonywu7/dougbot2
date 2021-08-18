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

from typing import Literal

from asgiref.sync import sync_to_async
from discord import User
from discord.ext.commands import group, is_owner

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext.common import Choice, doc
from ts2.discord.utils.common import Embed2

from ...models import BugReport, BugReportType
from ...models import User as WebUser


class Trac(
    Gear, name='Trac', order=75,
    description='',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @sync_to_async
    def get_web_user(self, user: User):
        return WebUser.objects.get(pk=user.id)

    @sync_to_async
    def format_bug_report(self, ctx: Circumstances, report: BugReport) -> Embed2:
        embed = (Embed2(title=f'Issue #{report.id}', description=report.summary)
                 .add_field(name='type', value=report.get_topic_display(), inline=True)
                 .add_field(name='command', value=report.path or '(none)', inline=True))
        user = ctx.bot.get_user(report.user_id)
        if user:
            embed = embed.personalized(user)
        else:
            embed = embed.set_author(name=str(report.user))
        return embed

    @group('bug', case_insensitive=True)
    @doc.description('Bug report.')
    @doc.restriction(is_owner)
    @doc.hidden
    async def bug(self, ctx: Circumstances):
        pass

    @bug.command('create')
    @doc.description('Create a new bug report.')
    @doc.hidden
    async def create_bug(
        self, ctx: Circumstances,
        topic: Choice[BugReportType.names, Literal['bug report type']],
        summary: str, path: str = '',
    ):
        @sync_to_async
        def save():
            report = BugReport(
                user_id=ctx.author.id,
                topic=getattr(BugReportType, topic),
                summary=summary, path=path,
            )
            report.save()
            return report

        report = await save()
        reply = await self.format_bug_report(ctx, report)
        return await ctx.reply(embed=reply)

    @bug.command('get')
    @doc.description('Get a bug report by its ID.')
    @doc.hidden
    async def get_bug(self, ctx: Circumstances, idx: int):
        @sync_to_async
        def get():
            return BugReport.objects.prefetch_related('user').get(pk=idx)

        try:
            report = await get()
        except BugReport.DoesNotExist:
            raise doc.NotAcceptable('Issue with this ID does not exist.')
        reply = await self.format_bug_report(ctx, report)
        return await ctx.reply(embed=reply)
