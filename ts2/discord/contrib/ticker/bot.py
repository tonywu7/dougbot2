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

import logging
from datetime import datetime, timezone
from typing import Literal, Optional, TypedDict, Union

import pendulum
from discord import (CategoryChannel, Forbidden, Guild, Member, StageChannel,
                     TextChannel, VoiceChannel, VoiceState)
from discord.ext import tasks
from discord.ext.commands import Greedy, group, has_guild_permissions
from jinja2 import TemplateError, TemplateSyntaxError

from ts2.discord import server
from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext import autodoc as doc
from ts2.discord.ext.common import (Choice, Constant, Datetime, Dictionary,
                                    JinjaTemplate, Timedelta, unpack_dict)
from ts2.discord.ext.template import CommandTemplate, get_environment
from ts2.discord.models import Channel
from ts2.discord.utils.async_ import (async_delete, async_get, async_list,
                                      async_save)
from ts2.discord.utils.common import (Embed2, EmbedPagination,
                                      PermissionOverride, chapterize, code,
                                      tag, tag_literal, timestamp, utcnow)

from .models import TickerChannel

AnyChannel = Union[TextChannel, VoiceChannel, StageChannel, CategoryChannel]
VCs = Union[VoiceChannel, StageChannel]


def _reason(s: str):
    return f'Channel hoisting: {s}'


async def _sync_channel(vc: VoiceChannel) -> Channel:
    c = Channel(
        snowflake=vc.id, name=vc.name, type=vc.type.value,
        guild_id=vc.guild.id, order=vc.position,
        category_id=vc.category_id,
    )
    await async_save(c)
    return c


class TickerState:
    def __init__(self, vc: VoiceChannel, ticker: TickerChannel):
        self.name: str = vc.name
        self.position: int = vc.position
        self.category: CategoryChannel = vc.category
        self.overwrites = {**vc.overwrites}
        self.placement: ChannelPlacement = {**ticker.placement}


async def _edit_vc_idempotent(
    target: VoiceChannel, ref: TickerState,
    reason: str, name: str = None,
):
    for k in ('name', 'position', 'category', 'overwrites'):
        if getattr(target, k) != getattr(ref, k):
            break
    else:
        if name is None:
            return
    await target.edit(
        reason=_reason(reason),
        name=name or ref.name,
        category=ref.category,
        overwrites=ref.overwrites,
    )
    await target.move(category=ref.category, **ref.placement)


class ChannelPlacement(TypedDict):
    beginning: Optional[bool]
    end: Optional[bool]
    offset: Optional[int]


class Ticker(
    Gear, name='Ticker', order=50,
    description='Manage \"news tickers\": display & hoist messages in the channel list',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger('discord.contrib.ticker')
        self.tasks: dict[int, tasks.Loop] = {}
        self.states: dict[int, TickerState] = {}
        self.errors: dict[int, tuple[datetime, Exception]] = {}

    def set_state(self, vc: VoiceChannel, ticker: TickerChannel):
        self.states[vc.id] = state = TickerState(vc, ticker)
        return state

    @Gear.listener('on_guild_available')
    async def resume_tasks(self, guild: Guild):
        q = TickerChannel.objects.filter(server_id__exact=guild.id)
        tickers: list[TickerChannel] = await async_list(q)

        for ticker in tickers:
            if ticker.pk in self.tasks:
                continue
            if ticker.expired:
                await self.delete_ticker(guild, ticker, 'expired')
            else:
                vc = guild.get_channel(ticker.pk)
                if vc:
                    await self.start_ticker(vc, ticker)
                else:
                    await self.restart_ticker(guild, ticker)

    @Gear.listener('on_guild_channel_delete')
    async def on_delete_remove_ticker(self, channel: VoiceChannel):
        try:
            ticker = await async_get(TickerChannel, channel_id=channel.id)
        except TickerChannel.DoesNotExist:
            pass
        else:
            await async_delete(ticker)
            await self.stop_ticker(channel.id)

    # @Gear.listener('on_guild_channel_update')
    # async def enforce_ticker_settings(self, before: VoiceChannel, after: VoiceChannel):
    #     stored = self.states.get(after.id)
    #     if not stored:
    #         return
    #     try:
    #         state = await _edit_vc_idempotent(after, stored, 'integrity')
    #     except Exception as e:
    #         self.log.error(f'Error restoring channel: {e}')
    #         return
    #     self.states[after.id] = state

    @Gear.listener('on_voice_state_update')
    async def enforce_ticker_empty(
        self, member: Member,
        before: VoiceState, after: VoiceState,
    ):
        channel: VoiceChannel = after.channel
        if not channel or channel.id not in self.states:
            return
        try:
            await member.edit(voice_channel=None, reason=_reason('integrity'))
        except Forbidden:
            ticker = await async_get(TickerChannel, channel_id=channel.id)
            return await self.restart_ticker(member.guild, ticker)

    async def create_ticker_channel(
        self, guild: Guild,
        category: Optional[CategoryChannel], placement: ChannelPlacement,
        content: CommandTemplate, variables: dict,
    ) -> VoiceChannel:
        if category:
            if not category.permissions_for(guild.me).view_channel:
                raise doc.NotAcceptable(
                    'The bot does not have the "View Channel" permission'
                    f' under category {category}.',
                )
        try:
            name = await content.render_timed(None, timeout=10, **variables)
        except TemplateError as e:
            raise doc.NotAcceptable(f'Error rendering template: {e}')
        everyone_perms = PermissionOverride(
            view_channel=True, manage_channels=False,
            connect=False, speak=False, stream=False, move_members=False,
        )
        self_perms = PermissionOverride(
            view_channel=True, manage_channels=True,
            move_members=True, connect=True, speak=True, stream=True,
        )
        override = {guild.default_role: everyone_perms,
                    guild.self_role: self_perms}
        kwargs = {'name': name, 'overwrites': override, 'category': category,
                  'reason': _reason('initial creation')}
        async with server.exclusive_sync():
            vc = await guild.create_voice_channel(**kwargs)
            await _sync_channel(vc)
        if placement:
            await vc.move(category=category, **placement)
        self.log.debug(f'Ticker channel created: {vc}')
        return vc

    async def create_ticker(
        self, vc: VoiceChannel, placement: ChannelPlacement,
        content: CommandTemplate, variables: dict,
        refresh: float, expire: datetime,
    ) -> TickerChannel:
        tmpl = content.source
        guild_id = vc.guild.id
        category_id = vc.category_id
        ticker = TickerChannel(
            channel_id=vc.id, parent_id=category_id, server_id=guild_id,
            placement=placement, content=tmpl, variables=variables,
            refresh=refresh, expire=expire,
        )
        await async_save(ticker)
        self.log.debug(f'Ticker created: {vc.id}')
        return ticker

    async def start_ticker(self, channel: VoiceChannel, ticker: TickerChannel):
        guild = channel.guild
        state = self.set_state(channel, ticker)

        if channel.id in self.tasks:
            await self.stop_ticker(ticker.pk)

        if ticker.expire:
            expire = ticker.expire
            now = utcnow()
            next_tick = (expire - now).total_seconds()

            @tasks.loop(seconds=next_tick, count=2)
            async def cancel_ticker():
                if ticker.expired:
                    await self.delete_ticker(guild, ticker, 'expired')

            cancel_ticker.start()

        if ticker.refresh:

            @tasks.loop(seconds=ticker.refresh)
            async def run_ticker():
                nonlocal state
                self.log.debug(f'Tick: {ticker.pk}')
                env = get_environment()
                tmpl = env.from_string(ticker.content)
                name = await tmpl.render_timed(None, 10, **ticker.variables)
                await _edit_vc_idempotent(channel, state, 'update', name)
                state = self.set_state(channel, ticker)
                self.errors.pop(channel.id, None)

            @run_ticker.error
            async def on_error(exc: Exception):
                self.log.warning(f'Error running ticker {ticker.pk}: {exc}')
                try:
                    exists = self.bot.get_channel(channel.id)
                    if not exists:
                        return await self.delete_ticker(guild, ticker, 'deleted')
                    self.errors[channel.id] = (utcnow(), exc)
                except Exception as e:
                    self.errors[channel.id] = (utcnow(), e)

            self.tasks[channel.id] = run_ticker
            run_ticker.start()

    async def stop_ticker(self, ticker_id: int):
        self.log.debug(f'Stopping ticker {ticker_id}')
        task = self.tasks.get(ticker_id)
        if not task:
            return
        task.cancel()
        self.tasks.pop(ticker_id, None)
        self.states.pop(ticker_id, None)

    async def restart_ticker(self, guild: Guild, ticker: TickerChannel) -> VoiceChannel:
        self.log.debug(f'Restarting ticker {ticker.pk}')
        await self.stop_ticker(ticker.pk)

        existing: Optional[VoiceChannel] = guild.get_channel(ticker.channel_id)

        category = guild.get_channel(ticker.parent_id)
        options = {
            'guild': guild,
            'category': category,
            'placement': {**ticker.placement},
            'content': get_environment().from_string(ticker.content),
            'variables': ticker.variables,
        }

        vc = await self.create_ticker_channel(**options)

        ticker.channel_id = vc.id
        ticker.parent_id = vc.category_id
        await async_save(ticker)

        await self.start_ticker(vc, ticker)

        if existing:
            await existing.delete(reason=_reason('restart'))
        return vc

    async def delete_ticker(self, guild: Guild, ticker: TickerChannel, reason: str):
        self.log.debug(f'Deleting ticker {ticker.pk}')
        channel = guild.get_channel(ticker.pk)
        await async_delete(ticker)
        if not channel:
            return
        try:
            await channel.delete(reason=_reason(reason))
        except Exception as e:
            self.log.warning(f'Error deleting ticker {channel.id}: {e}')
        await self.stop_ticker(ticker.pk)

    async def get_ticker_or_404(self, ctx: Circumstances, channel: VoiceChannel):
        tickers = TickerChannel.objects.filter(server_id__exact=ctx.guild.id)
        try:
            ticker: TickerChannel = await async_get(tickers, channel_id=channel.id)
        except TickerChannel.DoesNotExist:
            raise doc.NotAcceptable((f'{tag(channel)} is not a channel'
                                     ' hoisted with this command.'))
        else:
            return ticker

    @group('ticker', invoke_without_command=True)
    @doc.description('List all VCs currently used for message hoisting.')
    async def ticker(self, ctx: Circumstances):
        q = TickerChannel.objects.filter(server_id__exact=ctx.guild.id)
        tickers = await async_list(q)
        ticker_list: list[str] = []
        for c in tickers:
            error = self.errors.get(c.pk)
            if error:
                msg = f'{code(c.pk)} {tag_literal("channel", c.pk)}: Error: {error}'
            else:
                msg = f'{code(c.pk)} {tag_literal("channel", c.pk)}: Running'
            ticker_list.append(msg)
        ticker_list = '\n'.join(ticker_list)
        if not ticker_list:
            ticker_list = '(none)'
        embed = Embed2().decorated(ctx.guild)
        ticker_page = [embed.set_description(d) for d
                       in chapterize(ticker_list, 480)]
        pagination = EmbedPagination(ticker_page, 'News ticker channels')
        return (
            await ctx.response(ctx, embed=pagination)
            .responder(lambda m: pagination(ctx.bot, m, 300, ctx.author))
            .run()
        )

    def get_variables(self, param: Optional[Dictionary] = None,
                      default: Optional[dict] = None) -> Optional[dict]:
        return unpack_dict(param, default or {})

    def get_expire(
        self, expire_at: Optional[Datetime],
        expire_in: Optional[Timedelta], now: datetime,
        default: Optional[datetime] = None,
    ) -> Optional[datetime]:
        if expire_at:
            expire = expire_at.value
            if not expire.tzinfo:
                raise doc.NotAcceptable(
                    'Supplied expire time must include timezone'
                    ' info (or supply a duration instead).',
                )
            expire = expire.astimezone(timezone.utc)
        elif expire_in:
            delta = expire_in.value
            expire = now + delta
        else:
            expire = None

        if expire and expire <= now:
            raise doc.NotAcceptable('Expiration time cannot be in the past.')

        return expire

    def get_refresh(self, refresh: Optional[Timedelta],
                    default: float = 0) -> float:
        if refresh:
            refresh = refresh.value.total_seconds()
            if refresh < 300:
                raise doc.NotAcceptable('Minimum refresh interval is 5 minutes.')
        else:
            refresh = default
        return refresh

    def get_category(
        self, category: Optional[Union[AnyChannel, Constant[Literal['top']]]],
        default: Optional[CategoryChannel] = None,
    ) -> Optional[CategoryChannel]:
        if category is None:
            return default
        elif category == 'top':
            category = None
        elif not isinstance(category, CategoryChannel):
            category = category.category
        return category

    def get_placement(self, position: Optional[Union[int, Choice[Literal['append', 'prepend']]]],
                      default: Optional[ChannelPlacement] = None) -> Optional[ChannelPlacement]:
        if position is None:
            return default
        placement: ChannelPlacement = {}
        if position == 'prepend' or position == 0:
            placement['beginning'] = True
        elif position == 'append':
            placement['end'] = True
        elif position > 0:
            placement['beginning'] = True
            placement['offset'] = position - 1
        else:
            placement['end'] = True
            placement['offset'] = position
        return placement

    def get_template(self, content: Optional[Union[JinjaTemplate, str]],
                     default: Optional[str] = None) -> CommandTemplate:
        if content is None:
            content = default
        if isinstance(content, JinjaTemplate):
            content = content.result
        try:
            template = get_environment().from_string(content)
        except TemplateSyntaxError as e:
            raise doc.NotAcceptable(f'Invalid template: {e}')
        return template

    def get_result(self, vc: VoiceChannel, ticker: TickerChannel) -> Embed2:
        description = f'{tag(vc)} at {code(vc.id)}'
        if ticker.expire:
            expire = timestamp(ticker.expire, 'relative')
        else:
            expire = 'never'
        if ticker.refresh:
            duration = pendulum.duration(seconds=ticker.refresh)
            refresh = f'every {duration.in_words()}'
        else:
            refresh = 'no auto refresh'
        return (
            Embed2(title='Ticker', description=description)
            .add_field(name='Expire', value=expire)
            .add_field(name='Refresh', value=refresh)
            .decorated(vc.guild)
        )

    @ticker.command('create', aliases=('add', 'new'))
    @doc.description('Hoist a message in the channel list.')
    @doc.argument('category', (
        'A channel under the same category where the message will be added;'
        ' specify "top" to place it above all categories (uncategorized).'
    ), node='[channel]')
    @doc.argument('position', (
        'The position of the new ticker in its category, starting from 1'
        ' (e.g. if set to 1 then the new VC will the first one).'
    ))
    @doc.argument('expire_at', (
        'Time at which to auto delete the ticker.'
    ))
    @doc.argument('expire_in', (
        'Duration after which to delete the ticker;'
        ' ignored if expire_at is set.'
    ))
    @doc.argument('refresh', (
        'Interval at which to update the text of the ticker;'
        ' only useful when using a template with content that'
        ' changes with time; specify 0 to never refresh;'
        ' minimum is 5 minutes.'
    ), node='[interval]')
    @doc.argument('content', 'Text of the message.')
    @doc.argument('variables', (
        'Additional variables to be passed to the template;'
        ' only useful if the content specified is a Jinja template;'
        ' must be JSON-serializable.'
    ))
    @doc.use_syntax_whitelist
    @doc.invocation(('category', 'position', 'content'), None)
    @doc.example(
        '72-st append 86 Street',
        'Create a VC with the name "86 Street",'
        ' place it under the same category as channnel #72-st is in,'
        ' and move it to the end of the VC list.',
    )
    @doc.example(
        'top prepend 96 Street',
        'Create a VC with the name "96 Street" and place it at'
        ' the very top of the channel list.',
    )
    @doc.restriction(
        has_guild_permissions,
        manage_channels=True,
        manage_roles=True,
    )
    async def ticker_create(
        self, ctx: Circumstances,
        category: Union[AnyChannel, Constant[Literal['top']]],
        position: Union[int, Choice[Literal['append', 'prepend']]],
        *, content: Union[JinjaTemplate, str],
        expire_at: Optional[Datetime] = None,
        expire_in: Optional[Timedelta] = None,
        refresh: Optional[Timedelta] = None,
        variables: Optional[Dictionary] = None,
    ):
        variables = self.get_variables(variables)
        expire = self.get_expire(expire_at, expire_in, ctx.timestamp)
        refresh = self.get_refresh(refresh)
        category = self.get_category(category)
        placement = self.get_placement(position)
        template = self.get_template(content)

        async with ctx.typing():
            vc = await self.create_ticker_channel(ctx.guild, category,
                                                  placement, template, variables)
            ticker = await self.create_ticker(vc, placement, template, variables,
                                              refresh, expire)
            await self.start_ticker(vc, ticker)
            result = self.get_result(vc, ticker)
            return await ctx.response(ctx, embed=result).reply().deleter().run()

    @ticker.command('update', aliases=('set', 'edit'))
    @doc.description('Update settings for a currently running ticker.')
    @doc.argument('channel', (
        'The ticker to update;'
        ' must be a VC managed by this command.'
    ))
    @doc.argument('category', False)
    @doc.argument('position', False)
    @doc.argument('content', False)
    @doc.argument('expire_at', False)
    @doc.argument('expire_in', False)
    @doc.argument('refresh', False)
    @doc.argument('variables', False)
    @doc.use_syntax_whitelist
    @doc.invocation(('channel',), None)
    @doc.discussion(
        'Argument types', (
            'This command accepts the same set of arguments'
            ' as the ticker create command. To see what each argument does,'
            f' consult help for {code("ticker create")}.'
        ),
    )
    @doc.restriction(
        has_guild_permissions,
        manage_channels=True,
        manage_roles=True,
    )
    async def ticker_update(
        self, ctx: Circumstances,
        channel: VoiceChannel,
        category: Optional[Union[AnyChannel, Constant[Literal['top']]]] = None,
        position: Optional[Union[int, Choice[Literal['append', 'prepend']]]] = None,
        *, content: Optional[Union[JinjaTemplate, str]] = None,
        expire_at: Optional[Datetime] = None,
        expire_in: Optional[Timedelta] = None,
        refresh: Optional[Timedelta] = None,
        variables: Optional[Dictionary] = None,
    ):
        ticker = await self.get_ticker_or_404(ctx, channel)
        current_category = ctx.guild.get_channel(ticker.parent_id)
        category = self.get_category(category, current_category)
        ticker.category_id = category and category.id
        ticker.variables = self.get_variables(variables, ticker.variables)
        ticker.expire = self.get_expire(expire_at, expire_in, ctx.timestamp, ticker.expire)
        ticker.refresh = self.get_refresh(refresh, ticker.refresh)
        ticker.placement = self.get_placement(position, ticker.placement)
        ticker.content = self.get_template(content, ticker.content).source
        async with ctx.typing():
            vc = await self.restart_ticker(ctx.guild, ticker)
            result = self.get_result(vc, ticker)
            return await ctx.response(ctx, embed=result).reply().deleter().run()

    @ticker.command('delete', aliases=('rm', 'del', 'remove'))
    @doc.description('Remove a hoisted message.')
    @doc.argument('channels', 'The channel to remove.')
    @doc.restriction(
        has_guild_permissions,
        manage_channels=True,
        manage_roles=True,
    )
    async def ticker_remove(self, ctx: Circumstances, channels: Greedy[VoiceChannel]):
        deleted: list[str] = []
        async with ctx.typing():
            for channel in channels:
                try:
                    ticker = await self.get_ticker_or_404(ctx, channel)
                except doc.NotAcceptable:
                    continue
                channel_id = ticker.channel_id
                await self.delete_ticker(ctx.guild, ticker, 'manual_removal')
                deleted.append(str(channel_id))
            result = Embed2(description=f'Ticker deleted: {", ".join(deleted)}')
            return await ctx.response(ctx, embed=result).reply().deleter().run()
