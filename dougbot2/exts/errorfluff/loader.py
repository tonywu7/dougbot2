# errors.py
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

from arrow import Arrow
from discord import Forbidden, NotFound
from discord.abc import GuildChannel
from discord.ext.commands import errors

from ...blueprints import MissionControl, Surroundings
from ...utils.english import describe_concurrency
from ...utils.markdown import code, strong, tag_literal, verbatim
from . import utils

_SEPARATOR = "\n:warning: "


async def _on_command_not_found(ctx: Surroundings, exc: errors.CommandNotFound):
    """Reply with autocorrect suggestions when someone attempts to call a non-existing command."""
    if utils.is_direct_message(ctx):
        return False
    cmd = utils.full_invoked_with(ctx)
    if ctx.subcommand_passed:
        cmd = f"{cmd} {ctx.subcommand_passed}".strip()
    try:
        ctx.bot.manpage.find_command(cmd)
        return False
    except Exception as e:
        return str(e)


async def _on_cooldown(ctx, exc: errors.CommandOnCooldown):
    cooldown = exc.cooldown.per
    future = Arrow.utcnow().shift(seconds=cooldown)
    retry_in = future.humanize()
    return f"This command has a cooldown.\nTry again {retry_in}."


async def _on_max_concurrent(ctx, exc):
    return f"This command allows {describe_concurrency(exc.number, exc.per)}"


async def _on_missing_role(ctx, exc):
    return f'You are missing the {tag_literal("role", exc.missing_role)} role.'


async def _on_missing_any_role(ctx, exc: errors.MissingAnyRole):
    roles = utils.format_roles(exc.missing_roles)
    return f"You are missing at least one of the {roles} roles."


async def _on_bot_missing_role(ctx, exc: errors.MissingAnyRole):
    return f'The bot is missing the {tag_literal("role", exc.missing_role)} required to run this command.'


async def _on_bot_missing_any_role(ctx, exc: errors.BotMissingAnyRole):
    roles = utils.format_roles(exc.missing_roles)
    return f"The bot is missing the at least one of {roles} roles required to run this command."


async def _on_missing_perms(ctx, exc: errors.MissingPermissions):
    perms = utils.format_permissions(exc.missing_perms)
    try:
        channel: GuildChannel = exc.channel
    except AttributeError:
        where = ""
    else:
        where = f" in {channel.mention}"
    explanation = f"You are missing the {perms}{where}."
    return explanation


async def _on_bot_missing_perms(ctx, exc: errors.BotMissingPermissions):
    perms = utils.format_permissions(exc.missing_perms)
    try:
        channel: GuildChannel = exc.channel
    except AttributeError:
        where = ""
    else:
        where = f" in {channel.mention}"
    explaination = (
        f"The bot is missing the {perms}{where} required to run this command."
    )
    return explaination


async def _on_check_failure(ctx, exc: errors.CheckFailure):
    return f"You are not allowed to use this command:\n{exc}"


async def _on_check_any_failure(ctx, exc: errors.CheckAnyFailure):
    reasons = "\n".join([f"- {e}" for e in exc.errors])
    return f"You are not allowed to use this command:\n{reasons}"


async def _on_generic_parsing_error(ctx, exc: errors.ArgumentParsingError):
    return f"Error while parsing your command: {exc}"


async def _on_unexpected_eof(ctx, exc: errors.ExpectedClosingQuoteError):
    return f"Expected another {code(exc.close_quote)} at the end. Make sure your opening and closing quotes match."


async def _on_unexpected_quote(ctx, exc: errors.UnexpectedQuoteError):
    example = code('"There\\"s a quote in this sentence"')
    backslash = code("\\")
    msg = f"\n> {utils.indicate_eol(ctx)} :warning: Did not expect a {code(exc.quote)} here"
    msg = (
        f"{msg}\n\nIf you need to provide an argument with a double quote in it, "
        f"put a backslash {backslash} in front of the quote: {example}"
    )
    return msg


async def _on_unexpected_char_after_quote(
    ctx, exc: errors.InvalidEndOfQuotedStringError
):
    example = code('"There\\"s a quote in this sentence"')
    backslash = code("\\")
    msg = (
        f"\n> {utils.indicate_eol(ctx)} :warning: There should be a space before this "
        f"character {code(exc.char)} after the quote."
    )
    msg = (
        f"{msg}\n\nIf you need to provide an argument with a double quote in it, "
        f"put a backslash {backslash} in front of the quote: {example}"
    )
    return msg


async def _on_missing_args(ctx, exc: errors.MissingRequiredArgument):
    msg = f"Argument {strong(exc.param.name)} is needed but not provided."
    return f"{utils.indicate_next_arg(ctx, exc.param.name)}{_SEPARATOR}{msg}"


async def _on_too_many_args(ctx, exc: errors.TooManyArguments):
    msg = f'\n> {utils.indicate_next_arg(ctx)} :warning: {strong("Cannot parse this argument.")}'
    msg = f"{msg}\n\nMake sure you wrote your arguments correctly."
    return msg


async def _on_generic_conversion_error(ctx, exc: Exception):
    if exc.__cause__:
        msg = f"Error while parsing this argument: {exc.__cause__}"
    else:
        msg = "Error while parsing this argument."
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{msg}"


async def _explains_not_found(ctx: Surroundings, exc):
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{exc}"


async def _explains_emote_not_found(
    ctx: Surroundings, exc: errors.PartialEmojiConversionFailure
):
    msg = f"{verbatim(exc.argument)} is not an emote or is not in a valid Discord emote format."
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{msg}"


async def _explains_bad_invite(ctx: Surroundings, exc: errors.BadInviteArgument):
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{exc}"


async def _explains_bad_boolean(ctx: Surroundings, exc: errors.BadBoolArgument):
    msg = (
        verbatim(exc.argument)
        + " is not an acceptable answer to a true/false question in English.\n\n"
    ) + (
        "The following are considered to be true: "
        "yes, y, true, t, 1, enable, on\n"
        "The following are considered to be false: "
        "no, n, false, f, 0, disable, off"
    )
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{msg}"


async def _explains_channel_not_readable(ctx: Surroundings, exc):
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{exc}"


async def _explains_bad_color(ctx: Surroundings, exc: errors.BadColourArgument):
    example = code('"rgb(255, 255, 255)"')
    msg = (
        f"{exc}\n\nTo provide a color in the RGB format that also contains "
        f"spaces, be sure to quote it in double quotes: {example}"
    )
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{msg}"


async def _on_bad_union(ctx, exc: errors.BadUnionArgument):
    msg = "Could not recognize this argument as any of the above."
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{msg}"


async def _on_bad_args(ctx, exc):
    return f"{utils.indicate_this_arg(ctx)}{_SEPARATOR}{exc}"


async def _on_forbidden(ctx, exc):
    return f"The bot doesn't have the necessary server/channel permission to finish the command: {exc}"


async def _on_not_found(ctx, exc: NotFound):
    return f"Discord can't find the requested info: {exc}"


async def _on_nsfw_channel(ctx, exc):
    return "This command must only be used in a NSFW channel."


async def _on_exception(ctx, exc):
    return "Error while processing the command."


def setup(bot: MissionControl):
    """Create a default environment for reporting common bot exceptions."""
    err = bot.errorpage

    err.set_error_blurb(errors.CommandNotFound, _on_command_not_found)
    err.set_error_blurb(errors.CommandOnCooldown, _on_cooldown)
    err.set_error_blurb(errors.MaxConcurrencyReached, _on_max_concurrent)
    err.set_error_blurb(errors.MissingRole, _on_missing_role)
    err.set_error_blurb(errors.MissingAnyRole, _on_missing_any_role)
    err.set_error_blurb(errors.BotMissingRole, _on_bot_missing_role)
    err.set_error_blurb(errors.BotMissingAnyRole, _on_bot_missing_any_role)
    err.set_error_blurb(errors.MissingPermissions, _on_missing_perms)
    err.set_error_blurb(errors.BotMissingPermissions, _on_bot_missing_perms)
    err.set_error_blurb(errors.CheckFailure, _on_check_failure)
    err.set_error_blurb(errors.CheckAnyFailure, _on_check_any_failure)
    err.set_error_blurb(errors.ArgumentParsingError, _on_generic_parsing_error)
    err.set_error_blurb(errors.ExpectedClosingQuoteError, _on_unexpected_eof)
    err.set_error_blurb(errors.UnexpectedQuoteError, _on_unexpected_quote)
    err.set_error_blurb(
        errors.InvalidEndOfQuotedStringError, _on_unexpected_char_after_quote
    )
    err.set_error_blurb(errors.MissingRequiredArgument, _on_missing_args)
    err.set_error_blurb(errors.TooManyArguments, _on_too_many_args)
    err.set_error_blurb(errors.ConversionError, _on_generic_conversion_error)
    err.set_error_blurb(
        (
            errors.MessageNotFound,
            errors.MemberNotFound,
            errors.UserNotFound,
            errors.ChannelNotFound,
            errors.RoleNotFound,
            errors.EmojiNotFound,
        ),
        _explains_not_found,
    )
    err.set_error_blurb(errors.PartialEmojiConversionFailure, _explains_emote_not_found)
    err.set_error_blurb(errors.BadInviteArgument, _explains_bad_invite)
    err.set_error_blurb(errors.BadBoolArgument, _explains_bad_boolean)
    err.set_error_blurb(errors.ChannelNotReadable, _explains_channel_not_readable)
    err.set_error_blurb(errors.BadColourArgument, _explains_bad_color)
    err.set_error_blurb(errors.BadUnionArgument, _on_bad_union)
    err.set_error_blurb(errors.BadArgument, _on_bad_args)
    err.set_error_blurb(errors.NSFWChannelRequired, _on_nsfw_channel)
    err.set_error_blurb(Forbidden, _on_forbidden)
    err.set_error_blurb(NotFound, _on_not_found)
    err.set_error_blurb(Exception, _on_exception)

    err.add_error_fluff(errors.CommandNotFound, "Command not found")
    err.add_error_fluff(errors.CommandOnCooldown, "Command cooldown")
    err.add_error_fluff(
        errors.MaxConcurrencyReached, "Too many instances of this command running"
    )
    err.add_error_fluff(errors.MissingRole, "Missing roles")
    err.add_error_fluff(errors.MissingAnyRole, "Missing roles")
    err.add_error_fluff(errors.BotMissingRole, "Bot missing roles")
    err.add_error_fluff(errors.BotMissingAnyRole, "Bot missing roles")
    err.add_error_fluff(errors.MissingPermissions, "Missing perms")
    err.add_error_fluff(errors.BotMissingPermissions, "Bot missing perms")
    err.add_error_fluff(errors.CheckFailure, "Not allowed")
    err.add_error_fluff(errors.CheckAnyFailure, "Not allowed")
    err.add_error_fluff(errors.ArgumentParsingError, "Parsing error")
    err.add_error_fluff(errors.ExpectedClosingQuoteError, "No closing quote found")
    err.add_error_fluff(errors.UnexpectedQuoteError, "Unexpected quote")
    err.add_error_fluff(
        errors.InvalidEndOfQuotedStringError, "Missing spaces after quotes"
    )
    err.add_error_fluff(errors.MissingRequiredArgument, "Not enough arguments")
    err.add_error_fluff(errors.TooManyArguments, "Too many arguments")
    err.add_error_fluff(errors.ConversionError, "Parsing error")
    err.add_error_fluff(
        (
            errors.MessageNotFound,
            errors.MemberNotFound,
            errors.UserNotFound,
            errors.ChannelNotFound,
            errors.RoleNotFound,
            errors.EmojiNotFound,
        ),
        "Not found",
    )
    err.add_error_fluff(errors.PartialEmojiConversionFailure, "Emote not found")
    err.add_error_fluff(errors.BadInviteArgument, "Invalid invite")
    err.add_error_fluff(
        errors.BadBoolArgument, "Incorrect value to a true/false argument"
    )
    err.add_error_fluff(errors.ChannelNotReadable, "No access to channel")
    err.add_error_fluff(errors.BadColourArgument, "Incorrect color format")
    err.add_error_fluff(errors.BadUnionArgument, "Did not understand argument")
    err.add_error_fluff(errors.BadArgument, "Did not understand argument")
    err.add_error_fluff(errors.NSFWChannelRequired, "NSFW only")
    err.add_error_fluff(Forbidden, "Forbidden by Discord")
    err.add_error_fluff(NotFound, "Not found on Discord")
    err.add_error_fluff(Exception, "Error")

    def deferred() -> None:
        bot.console.ignore_exception(errors.NotOwner)
        bot.console.ignore_exception(errors.NoPrivateMessage)
        bot.console.ignore_exception(errors.PrivateMessageOnly)

    bot.defer_init(deferred)
