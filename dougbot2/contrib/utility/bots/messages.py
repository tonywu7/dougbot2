# messenger.py
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

import io
from datetime import timezone
from typing import Optional, Union

import simplejson as json
import toml
from discord import (
    AllowedMentions, Emoji, File, Message, Object, PartialEmoji, TextChannel,
)
from discord.ext.commands import Greedy, command, has_guild_permissions
from more_itertools import always_iterable, first

from dougbot2.blueprints import Surroundings
from dougbot2.contrib.replyutils import accept_reply
from dougbot2.exceptions import NotAcceptable
from dougbot2.exts import autodoc as doc
from dougbot2.utils.common import (
    Embed2, a, can_upload, code, strong, trunc_for_field,
)
from dougbot2.utils.converters import Dictionary, JinjaTemplate
from dougbot2.utils.datetime import localnow
from dougbot2.utils.discord_jinja import get_environment


def serialize_message(message: Message):
    """Export a discord.Message object as JSON."""
    author = message.author
    return {
        'id': message.id,
        'created_at': message.created_at.replace(tzinfo=timezone.utc).isoformat(),
        'author': {
            'id': author.id,
            'name': str(author),
            'display_name': author.display_name,
            'avatar_url': str(author.avatar_url),
        },
        'content': message.content,
        'embeds': [e.to_dict() for e in message.embeds],
        'files': [f.url for f in message.attachments],
    }


def get_allowed_mentions(info: dict) -> AllowedMentions:
    """Create a discord.AllowedMentions object from a dict specifying all options."""
    options = {}
    options['everyone'] = bool(info.get('everyone', False))
    roles = info.get('roles', False)
    if roles is True:
        options['roles'] = True
    elif roles:
        options['roles'] = role_ids = []
        for r in always_iterable(roles):
            role_ids.append(Object(id=str(r)))
    else:
        options['roles'] = False
    users = info.get('users', True)
    if users is True:
        options['users'] = True
    elif users:
        options['users'] = user_ids = []
        for u in always_iterable(users):
            user_ids.append(Object(id=str(u)))
    else:
        options['users'] = False
    options['replied_user'] = bool(info.get('replied_user', True))
    return AllowedMentions(**options)


class MessageCommands:
    """Commands for creating/manipulating messages."""
    # TODO: message edit command

    @command('stdout')
    @doc.description('Send a message to a channel.')
    @doc.argument('content', 'The text message to send.',
                  node='content', signature='content')
    @doc.argument('embed', 'The embed to send.',
                  node='embed', signature='embed',
                  term='TOML/JSON string')
    @doc.argument('channel', ('The channel to send the message to.'
                              ' If left blank, send to current channel.'))
    @doc.argument('mentions', ('The members/roles this message'
                               ' is allowed to notify.'))
    @doc.use_syntax_whitelist
    @doc.invocation(('content', 'channel'), None)
    @doc.invocation(('embed', 'channel'), None)
    @doc.invocation(('content', 'embed', 'channel'), None)
    @doc.restriction(
        has_guild_permissions,
        manage_messages=True,
        send_messages=True,
        attach_files=True,
        embed_links=True,
        mention_everyone=True,
    )
    async def stdout(
        self, ctx: Surroundings,
        content: Optional[str] = None,
        embed: Optional[dict] = None,
        channel: Optional[TextChannel] = None,
        *, mentions: Optional[dict] = None,
        reply: Optional[Message] = None,
        suppress_embeds: bool = False,
    ):
        if not content and not embed:
            return
        if embed:
            try:
                embed_obj = Embed2.from_dict(embed)
            except Exception as e:
                raise doc.NotAcceptable(f'Invalid embed: {e}')
        else:
            embed_obj = None
        if not channel:
            channel = ctx.channel
        if isinstance(mentions, dict):
            allowed_mentions = get_allowed_mentions(mentions)
        else:
            allowed_mentions = None
        if reply:
            ref = reply.to_reference(fail_if_not_exists=False)
        else:
            ref = None
        try:
            msg = await channel.send(content, embed=embed_obj, reference=ref,
                                     allowed_mentions=allowed_mentions)
            if suppress_embeds:
                await msg.edit(suppress=True)
        except Exception as e:
            raise doc.NotAcceptable(f'Failed to send message: {e}')
        url = a('Message created:', msg.jump_url)
        reply = Embed2(description=f'{url} {code(msg.id)}')
        await ctx.respond(embed=reply).reply().run()

    @command('stdin')
    @doc.description('Serialize a message to be used in the stdout command.')
    @doc.argument('message', 'The message to serialize.')
    @doc.use_syntax_whitelist
    @doc.invocation(('message',), None)
    @accept_reply('message')
    @can_upload
    async def stdin(
        self, ctx: Surroundings,
        message: Optional[Message],
    ):
        if not message:
            raise NotAcceptable('No message specified.')
        info = {'content': message.content}
        embed = first(message.embeds, None)
        if embed:
            info['embed'] = Embed2.upgrade(embed).to_dict()
        if message.reference and message.reference.resolved:
            info['reply'] = str(message.reference.resolved.id)
        info['mentions'] = {
            'everyone': str(bool(message.mention_everyone)),
            'roles': [str(r.id) for r in message.role_mentions],
            'users': [str(u.id) for u in message.mentions],
        }
        info['suppress_embeds'] = str(message.flags.suppress_embeds)
        with io.StringIO() as stream:
            toml.dump(info, stream)
            stream.seek(0)
            filename = f'message.{localnow().isoformat().replace(":", ".")}.toml'
            file = File(stream, filename=filename)
            await ctx.respond(files=[file]).run()

    @command('redirect')
    @doc.description('Copy the specified message to another channel.')
    @doc.argument('channel', 'The channel to send the message to.')
    @doc.argument('message', 'The message to copy.')
    @doc.argument('mentions', ('The members/roles this message'
                               ' is allowed to notify.'))
    @doc.use_syntax_whitelist
    @doc.invocation(('channel', 'message'), None)
    @doc.restriction(
        has_guild_permissions,
        manage_messages=True,
        send_messages=True,
        attach_files=True,
        embed_links=True,
        mention_everyone=True,
    )
    @accept_reply('message')
    async def redirect(
        self, ctx: Surroundings, channel: TextChannel,
        message: Optional[Message], *,
        mentions: Optional[dict] = None,
    ):
        if not message:
            raise NotAcceptable('No message specified.')
        content = message.content
        embed = first(message.embeds, None)
        files = [await att.to_file(spoiler=att.is_spoiler())
                 for att in message.attachments]
        if isinstance(mentions, dict):
            allowed_mentions = get_allowed_mentions(mentions)
        else:
            allowed_mentions = None
        msg = await channel.send(content=content, embed=embed, files=files,
                                 allowed_mentions=allowed_mentions)
        url = a('Message created:', msg.jump_url)
        reply = Embed2(description=f'{url} {code(msg.id)}')
        await ctx.respond(embed=reply).reply().run()

    @command('react')
    @doc.description('Add reactions to a message.')
    @doc.argument('message', 'The message to react to.')
    @doc.argument('emotes', 'The emotes to use. The bot must be able to use them.')
    @doc.use_syntax_whitelist
    @doc.invocation(('message', 'emotes'), None)
    @doc.restriction(
        has_guild_permissions,
        manage_messages=True,
        send_messages=True,
    )
    @accept_reply('message')
    async def react(
        self, ctx: Surroundings,
        message: Optional[Message],
        emotes: Greedy[Union[str, Emoji, PartialEmoji]],
    ):
        if not message:
            raise NotAcceptable('A message must be specified.')
        failed: list[PartialEmoji] = []
        for emote in emotes:
            try:
                await message.add_reaction(emote)
            except Exception:
                failed.append(emote)
        if failed:
            failed_list = '\n'.join(code(e) for e in failed)
            failed_list = trunc_for_field(failed_list, 1920)
            res = Embed2(description=f'{strong("Failed to add the following emotes")}\n{failed_list}')
            return await ctx.respond(embed=res).reply(True).run()

    @command('ofstream')
    @doc.description('Send the message content back as a text file.')
    @doc.argument('message', 'Another message whose content will be included.')
    @doc.use_syntax_whitelist
    @doc.invocation(('message',), None)
    @doc.hidden
    @can_upload
    @accept_reply('message')
    async def ofstream(
        self, ctx: Surroundings,
        message: Optional[Message],
        *, extras: str = None,
    ):
        info = []
        if ctx.raw_input or ctx.message.embeds or ctx.message.attachments:
            info.append(serialize_message(ctx.message))
        if message:
            info.append(serialize_message(message))
        if not info:
            return
        with io.StringIO() as stream:
            json.dump(info, stream, indent=' ')
            stream.seek(0)
            filename = f'message.{localnow().isoformat().replace(":", ".")}.json'
            file = File(stream, filename=filename)
            await ctx.respond(files=[file]).run()

    @command('render')
    @doc.description('Render a Jinja template.')
    @doc.argument('template', 'Jinja template string.')
    @doc.argument('variables', 'Context variables.')
    @doc.use_syntax_whitelist
    @doc.invocation(('template', 'variables'), None)
    @doc.hidden
    async def render(
        self, ctx: Surroundings,
        template: JinjaTemplate,
        variables: Optional[Dictionary],
    ):
        env = get_environment()
        if variables:
            variables = variables.result
        else:
            variables = {}
        try:
            await ctx.trigger_typing()
            tmpl = env.from_string(template.result)
            txt = await tmpl.render_timed(ctx, **variables)
            return await ctx.send(txt)
        except Exception as e:
            embed = ctx.bot.console.pprint_exception(e)
            tb = ctx.bot.console.dump_traceback(e)
            return await ctx.send(embed=embed, file=tb)
