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

import re
from operator import itemgetter
from typing import Optional, Union

from discord import (
    Guild,
    Member,
    Message,
    MessageReference,
    NotFound,
    Role,
    TextChannel,
)
from discord.ext.commands import (
    EmojiConverter,
    PartialEmojiConverter,
    RoleConverter,
    group,
    is_owner,
)
from more_itertools import padded

from dougbot2.discord.cog import Gear
from dougbot2.discord.context import Circumstances
from dougbot2.exts import autodoc as doc
from dougbot2.utils.async_ import async_delete, async_first, async_list, async_save
from dougbot2.utils.common import Embed2, a, code, strong, tag, tag_literal, verbatim

from .models import RoleCounter, RoleStatistics


class Rolemenu(
    Gear,
    name="Rolemenu",
    order=99,
    description="",
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    RE_ROLEMENU_LINE = re.compile(
        r"(?P<emote>\S+) +(?P<role>\S+) *(?P<description>.*)", re.MULTILINE
    )
    get_rolemenu_info = itemgetter("emote", "role", "description")

    def print_role_menu(
        self, guild: Guild, menu: RoleStatistics, *roles: RoleCounter
    ) -> str:
        lines: list[str] = [strong(menu.title), ""]
        if menu.description:
            lines.extend([menu.description, ""])
        for item in roles:
            role: Optional[Role] = guild.get_role(item.role_id)
            if not role:
                lines.append(
                    f'{item.emote} {tag_literal("role", item.id)} {item.description}'
                )
            else:
                lines.append(
                    f"{item.emote} {code(len(role.members))} {tag(role)} {item.description}"
                )
            lines.append("")
        lines.append("⠀")
        return "\n".join(lines)

    async def get_menu_from_message(self, message: Message) -> Optional[RoleStatistics]:
        q = (
            RoleStatistics.objects.filter(
                channel_id=message.channel.id, message_id=message.id
            )
            .prefetch_related("roles")
            .all()
        )
        return await async_first(q)

    @group("rolemenu", invoke_without_command=True)
    @doc.description("Create a role memu with counters.")
    @doc.restriction(is_owner)
    @doc.accepts_reply()
    @doc.hidden
    async def rolemenu(
        self,
        ctx: Circumstances,
        channel: TextChannel,
        *,
        formatted: str = "",
        reply: Optional[MessageReference],
    ):
        if not formatted:
            if not reply or not isinstance(reply.resolved, Message):
                raise doc.NotAcceptable("Formatted role menu required.")
            formatted = reply.resolved.content.strip()

        title, description, *lines = padded(formatted.split("\n"), "", 2)
        if not lines:
            raise doc.NotAcceptable("Too few lines.")

        emote_parser = EmojiConverter()
        role_parser = RoleConverter()
        roles: list[RoleCounter] = []
        for m in self.RE_ROLEMENU_LINE.finditer("\n".join(lines)):
            emote_arg, role_arg, role_desc = self.get_rolemenu_info(m)
            try:
                emote = await emote_parser.convert(ctx, m["emote"])
            except Exception:
                emote = emote_arg
            try:
                role = await role_parser.convert(ctx, role_arg)
            except Exception as e:
                raise doc.NotAcceptable(
                    f"Failed to convert {verbatim(role_arg)} to a role: {e}"
                )
            roles.append(
                RoleCounter(role_id=role.id, emote=str(emote), description=role_desc)
            )

        menu = RoleStatistics(title=title, description=description)
        output = self.print_role_menu(ctx.guild, menu, *roles)
        target: Message = await channel.send(output)

        menu.channel_id = target.channel.id
        menu.message_id = target.id

        try:
            menu: RoleStatistics = await async_save(menu)
            for counter in roles:
                counter.menu = menu
                counter.guild_id = ctx.guild.id
                await async_save(counter)
        except Exception:
            await target.delete(delay=0)
            raise

        res = Embed2(description=f"Role menu created: {a(target.id, target.jump_url)}")
        await ctx.response(ctx, embed=res).reply().run()

    @rolemenu.command("delete", aliases=("rm",))
    async def rolemenu_remove(self, ctx: Circumstances, message: Message):
        menu = await self.get_menu_from_message(message)
        if not menu:
            raise doc.NotAcceptable(f"Message {code(message.id)} is not a role menu.")
        await async_delete(menu)
        return await ctx.response(ctx).success().run()

    @rolemenu.command("edit-info")
    async def rolemenu_edit_info(self, ctx: Circumstances, msg: Message, title: str):
        menu = await self.get_menu_from_message(msg)
        if not menu:
            raise doc.NotAcceptable(f"Message {code(msg.id)} is not a role menu.")
        menu.title = title
        await async_save(menu)
        await msg.edit(content=self.print_role_menu(ctx.guild, menu, *menu.roles.all()))
        return await ctx.response(ctx).success().run()

    @rolemenu.command("edit-role")
    async def rolemenu_edit_role(
        self,
        ctx: Circumstances,
        msg: Message,
        emote: Union[PartialEmojiConverter, str],
        role: Role,
        *,
        description: str = "",
    ):
        menu = await self.get_menu_from_message(msg)
        if not menu:
            raise doc.NotAcceptable(f"Message {code(msg.id)} is not a role menu.")
        q = RoleCounter.objects.filter(menu_id=menu.pk, role_id=role.id)
        counter: Optional[RoleCounter] = await async_first(q)
        if not counter:
            raise doc.NotAcceptable(f"No such role {tag(role)} for menu {code(msg.id)}")
        counter.emote = str(emote)
        counter.role_id = role.id
        counter.description = description
        await async_save(counter)
        roles = [
            r if r.role_id != counter.role_id else counter for r in menu.roles.all()
        ]
        await msg.edit(content=self.print_role_menu(ctx.guild, menu, *roles))
        return await ctx.response(ctx).success().run()

    @Gear.listener("on_member_update")
    async def rolemenu_update(self, before: Member, after: Member):
        role_diff: set[int] = {r.id for r in set(before.roles) ^ set(after.roles)}
        if not role_diff:
            return
        guild: Guild = after.guild
        query = (
            RoleCounter.objects.filter(guild_id=guild.id)
            .prefetch_related("menu", "menu__roles")
            .all()
        )
        all_roles: list[RoleCounter] = await async_list(query)
        menus = {r.menu for r in all_roles if r.role_id in role_diff}
        for menu in menus:
            channel: Optional[TextChannel] = guild.get_channel(menu.channel_id)
            if not channel:
                continue
            message = channel.get_partial_message(menu.message_id)
            output = self.print_role_menu(guild, menu, *menu.roles.all())
            try:
                await message.edit(content=output)
            except NotFound:
                await async_delete(menu)
