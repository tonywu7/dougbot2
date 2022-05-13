# response.py
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
from collections.abc import Callable, Coroutine
from contextlib import suppress
from dataclasses import dataclass
from textwrap import shorten
from typing import Any, Optional

import attr
from discord import (
    AllowedMentions,
    DMChannel,
    Emoji,
    File,
    Forbidden,
    Message,
    MessageReference,
    PartialEmoji,
    TextChannel,
    User,
)
from discord.ext.commands import Context

from ..defaults import get_defaults
from .duckcord.embeds import Embed2
from .events import DeleteResponder, Responder, run_responders, start_responders
from .markdown import tag

logger = logging.getLogger("discord.utils.response")


@dataclass
class Fulfillment:
    message: Optional[Message]
    did_send_embed: bool
    did_send_attachments: bool
    did_add_reactions: bool

    @classmethod
    def none(cls):
        return cls(None, False, False, False)


@attr.s
class ResponseInit:
    """Utility class for specifying common command responses with a fluent interface.

    Each method except `run()` returns the object itself, allowing chaining.
    """

    context: Context = attr.ib()

    content: Optional[str] = attr.ib(default=None)
    embed: Optional[Embed2] = attr.ib(default=None)
    files: list[File] = attr.ib(default=attr.Factory(list))
    nonce: Optional[int] = attr.ib(default=None)

    delete_after: Optional[float] = attr.ib(default=None)
    allowed_mentions: Optional[AllowedMentions] = attr.ib(default=None)
    reference: Optional[Message | MessageReference] = attr.ib(default=None)
    mention_author: bool = attr.ib(default=False)

    callbacks: list[Callable[[Message], Coroutine]] = attr.ib(
        default=attr.Factory(list)
    )
    responders: list[Callable[[Message], Responder]] = attr.ib(
        default=attr.Factory(list)
    )
    indicators: list[Emoji | PartialEmoji | str] = attr.ib(default=attr.Factory(list))

    direct_message: bool = attr.ib(default=False)

    @classmethod
    def _attrs_filter(cls, att: attr.Attribute, val):
        return att.name in {
            "content",
            "embed",
            "files",
            "delete_after",
            "allowed_mentions",
            "reference",
            "mention_author",
        }

    def mentions(self, mentions: AllowedMentions | None):
        """Set the `allowed_mentions` parameter of the outgoing message."""
        if mentions is None:
            mentions = AllowedMentions.none()
        return attr.evolve(self, allowed_mentions=mentions)

    def reply(self, notify: bool = False):
        """Use Discord's reply feature when sending the response."""
        return attr.evolve(self, reference=self.context.message, mention_author=notify)

    def pingback(self):
        """Prepend the message content with a mention of the user calling the command."""
        content = self.content or ""
        content = f"{tag(self.context.author)} {content}"
        return attr.evolve(self, content=content)

    def responder(self, responder_init: Callable[[Message], Responder]):
        """Add a Responder to listen for events after the message is sent.

        The callback should take the resulting message and return a Responder.
        """
        init = attr.evolve(self)
        init.responders = [*self.responders, responder_init]
        return init

    def callback(self, cb: Callable[[Message], Coroutine[None, None, Any]]):
        """Add an arbitrary callback to be run after the message is sent.

        The callback should take the resulting message and return a coroutine.
        """
        init = attr.evolve(self)
        init.callbacks = [*self.callbacks, cb]
        return init

    def deleter(self):
        """Enable the deleter responder for this response.

        Allows the caller of the command to delete this response
        with a reaction.
        """
        return self.responder(lambda msg: DeleteResponder(self.context, msg))

    def autodelete(self, seconds: float):
        """Delete the response after this many seconds."""
        return attr.evolve(self, delete_after=seconds)

    def suppress(self, suppress=True):
        """Suppress/allow embeds in the response as soon as the message is sent."""

        if not suppress:
            return self

        async def callback(msg: Message):
            return await msg.edit(suppress=True)

        return self.callback(callback)

    def dm(self):
        """Set the response to DM the command caller instead of sending it to the current channel."""
        return attr.evolve(self, direct_message=True)

    def success(self):
        """React to the command invocation with a green checkmark indicating success."""
        return attr.evolve(
            self, indicators=[*self.indicators, get_defaults().styles.emotes.success]
        )

    def failure(self):
        """React to the command invocation with a red cross indicating failure/error."""
        return attr.evolve(
            self, indicators=[*self.indicators, get_defaults().styles.emotes.failure]
        )

    @property
    def is_empty(self) -> bool:
        """Whether no text, embed, nor file has been set for the response.

        Attempting to send a message at this state will fail.
        """
        return not self.content and not self.embed and not self.files

    async def _send_indicators(self) -> bool:
        res = await asyncio.gather(
            *[self.context.message.add_reaction(r) for r in self.indicators],
            return_exceptions=True,
        )
        return not any(isinstance(r, Exception) for r in res)

    async def _deliver(self) -> Fulfillment:
        """Deliver the response, with sensible permission tests."""
        target: TextChannel | DMChannel
        if self.direct_message:
            author: User = self.context.author
            if not (target := author.dm_channel):
                target = await author.create_dm()
        else:
            target = self.context.channel

        me: User = self.context.me
        perms = target.permissions_for(me)
        fulfilled = Fulfillment.none()
        if not perms.send_messages:
            return fulfilled

        params = attr.evolve(self)
        if params.embed is not None:
            fulfilled.did_send_embed = perms.embed_links
            if not perms.embed_links:
                params.content = "\n".join([params.content or "", str(params.embed)])
                params.embed = None
        if params.files:
            fulfilled.did_send_attachments = perms.attach_files
            if not perms.attach_files:
                params.files = []

        kwargs = attr.asdict(params, recurse=False, filter=self._attrs_filter)
        try:
            msg = await target.send(**kwargs)
            fulfilled.message = msg
            return fulfilled
        except Forbidden as e:
            logger.warning(f"Error while delivering response: {e}\n{self}")
            return Fulfillment.none()

    async def run(
        self, message: Optional[Message] = None, thread: bool = False
    ) -> Fulfillment:
        """Execute the response.

        Send out the message, run all callbacks, and begin listening for events.

        If `message` is specified, no message will be sent and callbacks
        and responders will run on this message instead.

        :param message: The message to react/listen, defaults to None
        :type message: Optional[Message], optional
        :param thread: If True, run responders in a separate thread,
            otherwise run them in the current event loop,
            defaults to True
        :type thread: bool, optional
        :return: The message that was sent and whether
            all embed, files, and reactions are sent successfully.
        :rtype: `Fulfillment`
        """
        did_set_indicators = bool(self.indicators) and await self._send_indicators()
        fulfilled = Fulfillment.none()
        fulfilled.message = message
        if not fulfilled.message:
            if self.is_empty:
                fulfilled.did_add_reactions = did_set_indicators
                return fulfilled
            fulfilled = await self._deliver()
        if not fulfilled.message:
            return fulfilled
        for cb in self.callbacks:
            with suppress(Exception):
                await cb(fulfilled.message)
        if self.responders:
            tasks = [r(fulfilled.message) for r in self.responders]
            if thread:
                start_responders(*tasks)
            else:
                await run_responders(*tasks)
        return fulfilled

    def __str__(self) -> str:
        target = self.context.author if self.direct_message else self.context.channel
        return (
            f"Response:\n target = {target}"
            f"\n content = {shorten(repr(self.content), 128)}"
            f"\n embed = {shorten(repr(self.embed), 128)}"
            f"\n files = {self.files}"
            f"\n indicators = {self.indicators}"
        )
