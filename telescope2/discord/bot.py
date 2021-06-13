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

from __future__ import annotations

import asyncio
import logging
import threading
from contextlib import contextmanager
from importlib import import_module
from pathlib import Path
from typing import (ContextManager, Dict, Generator, Generic, Iterable,
                    Optional, Protocol, Tuple, Type, TypeVar)

from asgiref.sync import sync_to_async
from discord import AllowedMentions, Client, Guild, Message, Permissions
from discord.abc import GuildChannel
from discord.ext.commands import Bot, Command, Group
from django.conf import settings
from django.core.cache import caches

from telescope2.utils.importutil import iter_module_tree, objpath

from . import ipc
from .apps import DiscordBotConfig
from .context import Circumstances
from .models import Server

T = TypeVar('T', bound=Client)
U = TypeVar('U', bound=Bot)


class CommandIterator(Protocol):
    commands: Iterable[Command]


class Robot(Bot):
    async def on_ready(self):
        self.log.info('Bot ready')
        self.log.info(f'User {self.user}')

    def iter_commands(
        self, root: Optional[CommandIterator] = None, prefix: str = '',
    ) -> Generator[Tuple[str, Command], None, None]:

        root = root or self
        for cmd in root.commands:
            identifier = f'{prefix}.{cmd.name}'
            yield (identifier, cmd)
            if isinstance(cmd, Group):
                yield from self.iter_commands(cmd, identifier)

    @classmethod
    def channels_ordered_1d(cls, guild: Guild) -> Generator[GuildChannel]:
        for cat, channels in guild.by_category():
            yield cat
            for c in channels:
                yield c


class Telescope(Robot):

    DEFAULT_PREFIX = 't;'
    DEFAULT_PERMS = Permissions(805825782)

    def __init__(self, *, loop: asyncio.AbstractEventLoop = None, **options):
        options['allowed_mentions'] = AllowedMentions(everyone=False, roles=False, users=True, replied_user=True)
        super().__init__(loop=loop, command_prefix=self.which_prefix, **options)

        self.log = logging.getLogger('telescope')
        self._register_events()
        self._register_commands()
        self._init_ipc()
        self._load_extensions()

    def _init_ipc(self):
        thread = ipc.CachePollingThread('discord')
        thread.add_event_listener('telescope2.discord.bot.refresh', sync_to_async(self._load_extensions))
        thread.start()

    def _register_events(self):
        return

    def _register_commands(self):
        for parts in iter_module_tree(str(Path(__file__).with_name('commands')), 1):
            module_path = f'.commands.{".".join(parts)}'
            command_module = import_module(module_path, __package__)
            try:
                command_module.register_all(self)
            except AttributeError:
                pass
            else:
                self.log.info(f'Loaded commands from {module_path}')

    @classmethod
    async def _get_prefix(cls, *, bot_id: int, guild_id: int):
        @sync_to_async
        def get():
            return Server.objects.get(pk=guild_id).prefix
        try:
            return [await get(), f'<@!{bot_id}> ']
        except Server.DoesNotExist:
            return [cls.DEFAULT_PREFIX, f'<@!{bot_id}> ']

    @classmethod
    async def which_prefix(cls, bot: Bot, msg: Message):
        bot_id = bot.user.id
        if msg.guild is None:
            return [cls.DEFAULT_PREFIX, f'<@!{bot_id}> ']
        return await cls._get_prefix(bot_id=bot_id, guild_id=msg.guild.id)

    @classmethod
    def schedule_refresh(cls):
        caches['discord'].set('telescope2.discord.bot.refresh', True)

    def _load_extensions(self, *args, **kwargs):
        app = DiscordBotConfig.get()
        for label, ext in app.ext_map.items():
            cog_cls = ext.target
            self.log.info(f'Loaded extension: {label} {objpath(cog_cls)}')
            self.add_cog(cog_cls(self))

    async def get_context(self, message, *, cls=Circumstances) -> Circumstances:
        ctx: Circumstances = await super().get_context(message, cls=cls)
        await ctx.init()
        return ctx


class BotRunner(threading.Thread, Generic[T]):
    def __init__(self, client_cls: Type[T], client_opts: Dict, run_forever=True, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._client_cls = client_cls
        self._client_options = client_opts
        self._run_forever = run_forever

        self.bot_init = threading.Condition()
        self.loop: asyncio.AbstractEventLoop
        self.client: T

    def run_client(self):
        with self.bot_init:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            client = self._client_cls(loop=loop, **self._client_options)
            self.loop = loop
            self.client = client
            self.bot_init.notify_all()
        if self._run_forever:
            loop.create_task(client.start(settings.DISCORD_BOT_TOKEN))
            loop.run_forever()

    def bot_initialized(self) -> bool:
        return hasattr(self, 'client')

    def run(self) -> None:
        return self.run_client()

    def join(self, timeout: Optional[float] = None) -> None:
        if hasattr(self, 'client'):
            self.loop.run_until_complete(self.client.close())
            self.loop.close()
        return super().join(timeout=timeout)

    @classmethod
    @contextmanager
    def instanstiate(cls, client_cls: Type[U], *args, run_forever=False, daemon=True, **kwargs) -> ContextManager[U]:
        thread = cls(client_cls, *args, run_forever=False, daemon=True, **kwargs)
        thread.start()
        with thread.bot_init:
            thread.bot_init.wait_for(thread.bot_initialized)
        try:
            yield thread.client
        finally:
            thread.join()
