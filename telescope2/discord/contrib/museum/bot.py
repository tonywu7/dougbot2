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

import re
import string
from collections import Counter
from typing import AsyncGenerator, List, Literal, Optional

import nltk
from asgiref.sync import sync_to_async
from discord import (AllowedMentions, Embed, Message, MessageReference, Object,
                     TextChannel)
from discord.ext.commands import BucketType
from django.conf import settings
from nltk.corpus import stopwords
from pendulum import DateTime, instance

from telescope2.discord import documentation as doc
from telescope2.discord.command import instruction
from telescope2.discord.context import Circumstances
from telescope2.discord.converters import Choice, InvalidSyntax
from telescope2.discord.documentation import NotAcceptable
from telescope2.discord.extension import Gear
from telescope2.discord.utils.markdown import (ParagraphStream, a, chapterize,
                                               strong, tag, tag_literal)
from telescope2.utils.datetime import utcnow
from telescope2.utils.db import async_atomic

from .models import StoryTask

BEGIN_OR_END = ('begin', 'end', 'start', 'stop')

RE_EXTRA_SPACE = re.compile(r'(\w+(?:\*|_|\||~|`)?) ([\.,/;\':"!?)\]}])( ?)')

TRANS_PUNCTUATIONS = str.maketrans({k: None for k in string.punctuation})


class Museum(Gear):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @instruction('story')
    @doc.description('Join multiple messages into a story.')
    @doc.argument('begin_or_end', node='begin/end')
    @doc.accepts_reply('Use the replied-to message as the start/end of the story.')
    @doc.use_syntax_whitelist
    @doc.invocation(('reply', 'begin_or_end'), 'Mark the replied-to message as the start/end of the story.')
    @doc.invocation(('begin_or_end', 'message'), 'Set the passed message as the start/end of the story. The message must be in the current channel.')
    @doc.concurrent(1, BucketType.channel)
    async def story(
        self, ctx: Circumstances,
        begin_or_end: Choice[BEGIN_OR_END, Literal['option']],
        message: Optional[Message],
        *, reply: Optional[MessageReference],
    ):
        if message is None and reply is None:
            raise InvalidSyntax(
                'Either you did not specify a message, '
                'or the message is not found, '
                'or is not readable by the bot.',
            )

        if reply:
            message: Message = reply.resolved
            if not message:
                message = ctx.channel.fetch_message(reply.message_id)
        elif message.channel != ctx.channel:
            raise NotAcceptable(f'Message {message.id} is not from this channel. '
                                f'It is from {tag(message.channel)}')

        if begin_or_end == 'start':
            begin_or_end = 'begin'
        if begin_or_end == 'stop':
            begin_or_end = 'end'

        SETUP_MSG = ('Story requested by %(author)s\n'
                     'Setting the %(side)s of the story '
                     'to %(msg_url)s in %(channel)s')
        REPLACE_MSG = (f'{SETUP_MSG}, ''replacing previously set marker '
                       'in %(set_channel)s')

        def as_noun(begin_or_end: str) -> str:
            return strong('beginning' if begin_or_end == 'begin' else 'end')

        msg_url = a(href=message.jump_url, text='this message')
        msg_id = message.id
        channel_id = ctx.channel.id
        channel = tag(ctx.channel)

        async with async_atomic():

            task, created = await self.story_fetch_task(ctx.author.id, begin_or_end, msg_id, channel_id)
            task: StoryTask

            reply_ctx = {'author': tag(ctx.author), 'side': as_noun(begin_or_end),
                         'msg_url': msg_url, 'channel': channel}

            if created:
                reply = SETUP_MSG % reply_ctx
                embed = Embed(title='New story', description=reply)
                return await ctx.reply(embed=embed)

            set_channel = tag_literal('channel', task.channel)

            if task.marked_as == begin_or_end:
                reply = REPLACE_MSG % {**reply_ctx, 'set_channel': set_channel}
                await self.story_set_task(task, msg_id, channel_id)
                embed = Embed(title='New story', description=reply)
                return await ctx.reply(embed=embed)

            if task.channel != channel_id:
                reply = ('The beginning and ending messages are not in the same channel:\n'
                         f'The {as_noun(begin_or_end)} is set in {channel}.\n'
                         f'The {as_noun(task.marked_as)} is set in {set_channel}.')
                raise NotAcceptable(reply)

        target_channel = ctx.guild.get_channel(task.channel)
        if target_channel is None:
            await self.story_del_task(task)
            raise NotAcceptable(f'Channel {task.channel} no longer exists or is not in the server.')

        async with ctx.typing():
            collector = StoryCollector(ctx)
            await collector(target_channel, task.message, msg_id)
            await self.story_del_task(task)

    @sync_to_async
    def story_fetch_task(self, user_id: int, marked_as: str, msg_id: int, channel_id: int) -> StoryTask:
        return StoryTask.objects.get_or_create(defaults={'marked_as': marked_as, 'message': msg_id,
                                                         'channel': channel_id}, user=user_id)

    @sync_to_async
    def story_set_task(self, task: StoryTask, msg_id: int, channel_id: int) -> StoryTask:
        task.message = msg_id
        task.channel = channel_id
        task.save()

    @sync_to_async
    def story_del_task(self, task: StoryTask) -> StoryTask:
        task.delete()


class StoryCollector:
    def __init__(self, ctx: Circumstances):
        self.STOPWORDS = stopwords.words('english')
        self.ctx = ctx
        self.stream = ParagraphStream()
        self.overflow = False
        self.messages: List[Message] = []
        self.story: str = ''

    @classmethod
    async def iter_messages(cls, channel: TextChannel, begin_id: int, end_id: int) -> AsyncGenerator[Message, None, None]:
        if begin_id > end_id:
            swap = begin_id
            begin_id = end_id
            end_id = swap
        current_id = begin_id - 1
        current = Object(current_id)
        while current_id < end_id:
            message: Message = None
            async for message in channel.history(limit=100, after=current):
                yield message
                if message.id >= end_id:
                    return
            if message is None:
                return
            current_id = message.id
            current = Object(current_id)

    async def _warn(self, message: str):
        warn = Embed(description=f'⚠️ {message}')
        await self.ctx.reply_with_delete(embed=warn, allowed_mentions=self.ctx.NOTIFY_REPLY)

    async def __call__(self, channel: TextChannel, begin_id: int, end_id: int, maxlen=8192):
        async for msg in self.iter_messages(channel, begin_id, end_id):
            self.messages.append(msg)
            self.stream.append(msg.content)
            if len(self.stream) >= maxlen:
                self.overflow = True
                break

        if not self.messages:
            return await self._warn('No message collected!')

        story = self.gen_story()
        if not story or story.isspace():
            return await self._warn('Gathered no text from all messages!')

        for chapter in chapterize(self.gen_story()):
            await self.ctx.send(chapter, allowed_mentions=AllowedMentions.none())
        await self.ctx.reply(embed=self.gen_stats(), allowed_mentions=self.ctx.NOTIFY_REPLY)

        if self.overflow:
            warn = (f'Length limit ({maxlen} characters) reached.\n'
                    f'Stopped at [this message]({msg.jump_url})')
            return await self._warn(warn)

    def fix_punctuations(self, text: str) -> str:
        return RE_EXTRA_SPACE.sub(r'\1\2\3', text)

    def gen_story(self) -> str:
        story = '\n'.join([*self.stream])
        story = self.fix_punctuations(story)
        self.story = story
        return story

    def gen_stats(self) -> Embed:
        if not self.messages or not self.story:
            raise ValueError('Story is empty')

        msgs_by_authors = Counter()
        msgs_by_authors.update([m.author for m in self.messages])

        unpunctuated = self.story.translate(TRANS_PUNCTUATIONS)
        tokens = [word.lower() for word in nltk.tokenize.word_tokenize(unpunctuated)]
        tokens_filtered = [t for t in tokens if t not in self.STOPWORDS]
        token_counter = Counter(tokens_filtered)

        contributors = ', '.join(sorted(tag(au) for au in msgs_by_authors))
        top_5_authors_msgs = ', '.join([f'{tag(au)} ({n})' for au, n in msgs_by_authors.most_common(5)])
        most_common_words = ', '.join([f'{word} ({n})' for word, n in token_counter.most_common(5)])

        start_msg = self.messages[0]
        end_msg = self.messages[-1]
        dt_start: DateTime = instance(start_msg.created_at).in_timezone(settings.TIME_ZONE)
        dt_end: DateTime = instance(end_msg.created_at).in_timezone(settings.TIME_ZONE)
        description = (f'Story in {tag(self.ctx.channel)} '
                       f'from {a(start_msg.jump_url, dt_start.format("D MMM Y at HH:mm:ss zz"))} '
                       f'to {a(end_msg.jump_url, dt_end.format("D MMM Y at HH:mm:ss zz"))}')

        stat = Embed(title='📊 Statistics', description=description)
        stat.add_field(name='Word count', value=len(tokens))
        stat.add_field(name='Character count', value=len(self.story))
        for contrib in chapterize(contributors, 960):
            stat.add_field(name='Contributors', value=contrib, inline=False)
        stat.add_field(name='Top 5 contributors by messages', value=top_5_authors_msgs, inline=False)
        stat.add_field(name='Most frequent terms', value=most_common_words, inline=False)
        stat.set_author(name=self.ctx.me.display_name, icon_url=self.ctx.me.avatar_url)
        stat.set_footer(text='Story collector')
        stat.timestamp = utcnow()
        return stat
