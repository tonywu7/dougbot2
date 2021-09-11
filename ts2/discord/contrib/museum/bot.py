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
from collections.abc import AsyncGenerator
from typing import Literal, Optional

import nltk
from asgiref.sync import sync_to_async
from discord import Message, MessageReference, Object, TextChannel
from discord.ext.commands import BucketType, command
from django.conf import settings
from nltk.corpus import stopwords
from pendulum import DateTime, instance

from ts2.discord.cog import Gear
from ts2.discord.context import Circumstances
from ts2.discord.ext.autodoc.exceptions import NotAcceptable
from ts2.discord.ext.common import Constant, doc
from ts2.discord.utils.duckcord.embeds import Embed2
from ts2.discord.utils.markdown import a, strong, tag, tag_literal, timestamp
from ts2.discord.utils.pagination import (EmbedPagination, ParagraphStream,
                                          chapterize, trunc_for_field)

from .models import StoryTask

RE_EXTRA_SPACE = re.compile(r'(\w+(?:\*|_|\||~|`)?) ([\.,/;\':"!?)\]}])( ?)(?!\w)')

TRANS_PUNCTUATIONS = str.maketrans({k: None for k in string.punctuation})


class Museum(
    Gear, name='Museum', order=11,
    description='Curation & archival',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @command('quote')
    @doc.description('Quote another message.')
    @doc.argument('message', 'The message to quote.')
    @doc.accepts_reply('Quote the replied-to message.')
    @doc.invocation(('message',), None)
    async def quote(
        self, ctx: Circumstances,
        message: Optional[Message],
        *, reply: Optional[MessageReference],
    ):
        if not message:
            if reply and reply.resolved:
                message = reply.resolved
        if not message:
            raise doc.NotAcceptable('You need to specify the message to quote.')
        header = f'{a(strong("Message"), message.jump_url)} in {tag(message.channel)}\n'
        content = message.content or message.system_content or '(no text content)'
        body = trunc_for_field(f'{header}{content}', 1960)
        res = Embed2(description=body)
        image = False
        attachments = []
        for att in message.attachments:
            if not image and att.content_type.startswith('image/'):
                res = res.set_image(url=att.url)
                image = True
            attachments.append(a(att.filename, att.url))
        if attachments:
            res = res.add_field(name='Attachments', value=' / '.join(attachments))
        res = (res.personalized(message.author)
               .set_footer(text='Original message sent:')
               .set_timestamp(message.created_at))
        embeds = [res, *[(Embed2.from_dict(e.to_dict())
                          .set_author_url(message.jump_url)
                          .set_footer(text=f'From message {message.id}, sent:')
                          .set_timestamp(message.created_at))
                         for e in message.embeds]]
        if message.embeds and not message.content and not message.attachments:
            embeds = embeds[1:]
        pages = EmbedPagination(embeds, None, False)
        return (await ctx.response(ctx, embed=pages)
                .responder(pages.with_context(ctx)).deleter().run())

    @command('story')
    @doc.description('Join multiple messages into a story.')
    @doc.accepts_reply('Use the replied-to message as the beginning of the story.')
    @doc.use_syntax_whitelist
    @doc.invocation(('message',), (
        'Mark the message (passed as a URL or ID) as the beginning of the story.'
    ))
    @doc.invocation(('reply',), (
        'Mark the replied-to message as the beginning of the story.'
    ))
    @doc.invocation(('message', 'cancel'), 'Remove a previously set marker.')
    @doc.concurrent(1, BucketType.channel)
    async def story(
        self, ctx: Circumstances,
        message: Optional[Message],
        cancel: Optional[Constant[Literal['cancel']]],
        *, reply: Optional[MessageReference],
    ):
        if message is None and reply is None:
            raise NotAcceptable(
                'You need to specify the message where the story'
                ' will begin by either passing its URL or message ID'
                ' or replying to it.\nIf you did specify it, the bot may not'
                ' have access to that message.',
            )

        if reply:
            message: Message = reply.resolved
            if not message:
                message = ctx.channel.fetch_message(reply.message_id)
        elif message.channel != ctx.channel:
            raise NotAcceptable(f'Message {message.id} is not from this channel. '
                                f'It is from {tag(message.channel)}')

        SETUP_MSG = ('Story requested by %(author)s'
                     '\nSetting the %(side)s of the story'
                     ' to %(msg_url)s in %(channel)s')
        DELETE_MSG = ('Story marker %(msg_url)s in %(channel)s'
                      ' removed (set by %(author)s)')

        msg_url = a('this message', href=message.jump_url)
        msg_id = message.id
        channel_id = ctx.channel.id
        channel = tag(ctx.channel)

        task, created = await self.story_fetch_task(ctx.author.id, msg_id, channel_id)
        task: StoryTask

        reply_ctx = {'author': tag(ctx.author), 'side': 'beginning',
                     'msg_url': msg_url, 'channel': channel}

        if created:
            reply = SETUP_MSG % reply_ctx
            embed = Embed2(title='New story', description=reply)
            return await ctx.response(ctx, embed=embed).deleter().run()

        set_channel = tag_literal('channel', task.channel)

        if cancel:
            reply = DELETE_MSG % reply_ctx
            await self.story_del_task(task)
            embed = Embed2(title='Reset story', description=reply)
            return await ctx.response(ctx, embed=embed).deleter().run()

        if task.channel != channel_id:
            reply = ('The beginning and ending messages are not in the same channel:'
                     f'\nThe beginning is set in {set_channel}'
                     f'\nbut the end is set in {channel}.')
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
    def story_fetch_task(self, user_id: int, msg_id: int, channel_id: int) -> StoryTask:
        return StoryTask.objects.get_or_create(defaults={
            'message': msg_id,
            'channel': channel_id,
        }, user=user_id)

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
        self.messages: list[Message] = []
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
        warn = Embed2(description=f'⚠️ {message}')
        await self.ctx.response(self.ctx, embed=warn).reply(notify=True).deleter().run()

    async def __call__(self, channel: TextChannel, begin_id: int, end_id: int, maxlen=2048):
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

        for chapter in chapterize(self.gen_story(), closing='...', opening='(continued) '):
            await (self.ctx.response(self.ctx, content=chapter)
                   .mentions(None).reply(True).suppress().run())
        await self.ctx.response(self.ctx, embed=self.gen_stats()).reply(notify=True).run()

        if self.overflow:
            warn = (f'Length limit ({maxlen} characters) reached.\n'
                    f'Stopped at {a("this message", msg.jump_url)}')
            return await self._warn(warn)

    def fix_punctuations(self, text: str) -> str:
        return RE_EXTRA_SPACE.sub(r'\1\2\3', text)

    def gen_story(self) -> str:
        story = '\n'.join([*self.stream])
        story = self.fix_punctuations(story)
        self.story = story
        return story

    def gen_stats(self) -> Embed2:
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
                       f'from {a(timestamp(dt_start, "long"), start_msg.jump_url)} '
                       f'to {a(timestamp(dt_end, "long"), end_msg.jump_url)}')

        stat = (
            Embed2(title='📊 Statistics', description=description)
            .set_timestamp()
            .add_field(name='Messages', value=len(self.messages))
            .add_field(name='Words', value=len(tokens))
            .add_field(name='Characters', value=len(self.story))
            .set_footer(text='Story collector')
            .decorated(self.ctx.guild)
        )
        for contrib in chapterize(contributors, 960):
            stat = stat.add_field(name='Contributors', value=contrib, inline=False)
        stat = stat.add_field(name='Top 5 contributors by messages', value=top_5_authors_msgs, inline=False)
        if most_common_words:
            stat = stat.add_field(name='Most frequent terms', value=most_common_words, inline=False)
        return stat
