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

from discord import Forbidden, NotFound
from discord.abc import GuildChannel
from discord.ext.commands import Context, errors

from ...utils.datastructures import TypeDictionary
from ...utils.english import describe_concurrency
from ...utils.markdown import code, escape_markdown, strong, tag_literal
from . import utils
from .environment import Environment, ErrorDict, ExceptionHandler, ReplyDict

_SEPARATOR = '\n⚠️ '


async def _on_command_not_found(ctx: Context, exc: errors.CommandNotFound):
    """Reply with autocorrect suggestions when someone attempts to call a non-existing command."""
    if utils.is_direct_message(ctx):
        return False
    cmd = utils.full_invoked_with(ctx)
    if ctx.subcommand_passed:
        cmd = f'{cmd} {ctx.subcommand_passed}'.strip()
    try:
        ctx.bot.manual.lookup(cmd)
        return False
    except Exception as e:
        return str(e)


async def _on_cooldown(env, ctx, exc: errors.CommandOnCooldown):
    cooldown = exc.cooldown.per
    try:
        from pendulum import duration
    except ModuleNotFoundError:
        cooldown_words = f'{cooldown:.0f}s'
        retry_words = f'{exc.retry_after:.0f}s'
    else:
        cooldown_words = duration(seconds=cooldown).in_words()
        retry_words = duration(seconds=exc.retry_after).in_words()
    return (f'This command has a cooldown of {cooldown_words}\n'
            f'Try again in {retry_words}')


async def _on_max_concurrent(env, ctx, exc):
    return f'This command allows {describe_concurrency(exc.number, exc.per)}'


async def _on_missing_role(env, ctx, exc):
    return f'You are missing the {tag_literal("role", exc.missing_role)} role.'


async def _on_missing_any_role(env, ctx, exc: errors.MissingAnyRole):
    roles = utils.format_roles(exc.missing_roles)
    return f'You are missing at least one of the {roles} roles.'


async def _on_bot_missing_role(env, ctx, exc: errors.MissingAnyRole):
    return (f'The bot is missing the {tag_literal("role", exc.missing_role)}'
            ' required to run this command.')


async def _on_bot_missing_any_role(ctx, exc: errors.BotMissingAnyRole):
    roles = utils.format_roles(exc.missing_roles)
    return (f'The bot is missing the at least one of {roles} roles'
            ' required to run this command.')


async def _on_missing_perms(env, ctx, exc: errors.MissingPermissions):
    perms = utils.format_permissions(exc.missing_perms)
    try:
        channel: GuildChannel = getattr(exc, 'channel')
    except AttributeError:
        where = ''
    else:
        where = f' in {channel.mention}'
    explanation = f'You are missing the {perms}{where}.'
    return explanation


async def _on_bot_missing_perms(env, ctx, exc: errors.BotMissingPermissions):
    perms = utils.format_permissions(exc.missing_perms)
    try:
        channel: GuildChannel = getattr(exc, 'channel')
    except AttributeError:
        where = ''
    else:
        where = f' in {channel.mention}'
    explaination = (f'The bot is missing the {perms}{where}'
                    f' required to run this command.')
    return explaination


async def _on_check_failure(env, ctx, exc: errors.CheckFailure):
    return f'You are not allowed to use this command:\n{exc}'


async def _on_check_any_failure(env, ctx, exc: errors.CheckAnyFailure):
    reasons = '\n'.join([f'- {e}' for e in exc.errors])
    return f'You are not allowed to use this command:\n{reasons}'


async def _on_generic_parsing_error(env, ctx, exc: errors.ArgumentParsingError):
    return f'Error while parsing your command: {exc}'


async def _on_unexpected_eof(env, ctx, exc: errors.ExpectedClosingQuoteError):
    return (f'Expected another {code(exc.close_quote)} at the end. '
            'Make sure your opening and closing quotes match.')


async def _on_unexpected_quote(ctx, exc: errors.UnexpectedQuoteError):
    example = code('"There\\"s a quote in this sentence"')
    backslash = code('\\')
    msg = f'\n> {utils.indicate_eol(ctx)} ⚠️ Did not expect a {code(exc.quote)} here'
    msg = (f'{msg}\n\nIf you need to provide an argument with a double quote in it, '
           f'put a backslash {backslash} in front of the quote: {example}')
    return msg


async def _on_unexpected_char_after_quote(ctx, exc: errors.InvalidEndOfQuotedStringError):
    example = code('"There\\"s a quote in this sentence"')
    backslash = code('\\')
    msg = (f'\n> {utils.indicate_eol(ctx)} ⚠️ There should be a space before this '
           f'character {code(exc.char)} after the quote.')
    msg = (f'{msg}\n\nIf you need to provide an argument with a double quote in it, '
           f'put a backslash {backslash} in front of the quote: {example}')
    return msg


async def _on_missing_args(ctx, exc: errors.MissingRequiredArgument):
    msg = f'Argument {strong(exc.param.name)} is needed but not provided.'
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _on_too_many_args(ctx, exc: errors.TooManyArguments):
    example_correct = code('poll "Bring back Blurple"')
    example_incorrect = f'{code("poll Bring back Blurple")} (will be recognized as 3 arguments)'
    msg = f'\n> {utils.indicate_next_arg(ctx)} ⚠️ {strong("Unrecognized argument found.")}'
    msg = (f'{msg}\n\nMake sure you spelled arguments correctly.'
           '\n\nIf some of the arguments have spaces in them '
           '(e.g. role names or nicknames), you will need to quote them in double quotes:\n'
           f'✅ {example_correct}\n🔴 {example_incorrect}')
    return msg


async def _on_generic_conversion_error(ctx, exc: Exception):
    if exc.__cause__:
        msg = f'Error while parsing this argument: {exc.__cause__}'
    else:
        msg = 'Error while parsing this argument.'
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _explains_not_found(ctx: Context, exc):
    msg = escape_markdown(str(exc))
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _explains_emote_not_found(ctx: Context, exc: errors.PartialEmojiConversionFailure):
    msg = f'{escape_markdown(exc.argument)} is not an emote or is not in a valid Discord emote format.'
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _explains_bad_invite(ctx: Context, exc: errors.BadInviteArgument):
    msg = strong(escape_markdown(str(exc)))
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _explains_bad_boolean(ctx: Context, exc: errors.BadBoolArgument):
    msg = (
        (strong(escape_markdown(exc.argument))
         + ' is not an acceptable answer to a true/false question in English.\n\n')
        + ('The following are considered to be true: '
           'yes, y, true, t, 1, enable, on\n'
           'The following are considered to be false: '
           'no, n, false, f, 0, disable, off')
    )
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _explains_channel_not_readable(ctx: Context, exc):
    msg = escape_markdown(str(exc))
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _explains_bad_color(ctx: Context, exc: errors.BadColourArgument):
    example = code('"rgb(255, 255, 255)"')
    msg = (f'{strong(escape_markdown(str(exc)))}\n\nTo provide a color in the RGB format that also contains '
           f'spaces, be sure to quote it in double quotes: {example}')
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _on_bad_union(ctx, exc: errors.BadUnionArgument):
    msg = 'Could not recognize this argument as any of the above.'
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _on_bad_args(ctx, exc):
    msg = escape_markdown(str(exc))
    return f'{utils.indicate_next_arg(ctx)}{_SEPARATOR}{msg}'


async def _on_forbidden(ctx, exc):
    return ("The bot doesn't have the necessary server/channel permission"
            f' to finish the command: {exc}')


async def _on_not_found(ctx, exc: NotFound):
    return f"Discord can't find the requested info: {exc}"


async def _on_nsfw_channel(env, ctx, exc):
    return 'This command must only be used in a NSFW channel.'


async def _on_exception(ctx, exc):
    return 'Error while processing the command.'


def default_env() -> Environment:
    """Create a default environment for reporting common bot exceptions."""
    errordict: ErrorDict = TypeDictionary()
    replies: ReplyDict = TypeDictionary()

    ignored = {
        errors.NotOwner,
        errors.NoPrivateMessage,
        errors.PrivateMessageOnly,
    }

    handlers: dict[type[Exception], ExceptionHandler] = {
        errors.CommandNotFound: _on_command_not_found,
        errors.CommandOnCooldown: _on_cooldown,
        errors.MaxConcurrencyReached: _on_max_concurrent,
        errors.MissingRole: _on_missing_role,
        errors.MissingAnyRole: _on_missing_any_role,
        errors.BotMissingRole: _on_bot_missing_role,
        errors.BotMissingAnyRole: _on_bot_missing_any_role,
        errors.MissingPermissions: _on_missing_perms,
        errors.BotMissingPermissions: _on_bot_missing_perms,
        errors.CheckFailure: _on_check_failure,
        errors.CheckAnyFailure: _on_check_any_failure,
        errors.ArgumentParsingError: _on_generic_parsing_error,
        errors.ExpectedClosingQuoteError: _on_unexpected_eof,
        errors.UnexpectedQuoteError: _on_unexpected_quote,
        errors.InvalidEndOfQuotedStringError: _on_unexpected_char_after_quote,
        errors.MissingRequiredArgument: _on_missing_args,
        errors.TooManyArguments: _on_too_many_args,
        errors.ConversionError: _on_generic_conversion_error,
        (errors.MessageNotFound,
         errors.MemberNotFound,
         errors.UserNotFound,
         errors.ChannelNotFound,
         errors.RoleNotFound,
         errors.EmojiNotFound): _explains_not_found,
        errors.PartialEmojiConversionFailure: _explains_emote_not_found,
        errors.BadInviteArgument: _explains_bad_invite,
        errors.BadBoolArgument: _explains_bad_boolean,
        errors.ChannelNotReadable: _explains_channel_not_readable,
        errors.BadColourArgument: _explains_bad_color,
        errors.BadUnionArgument: _on_bad_union,
        errors.BadArgument: _on_bad_args,
        errors.NSFWChannelRequired: _on_nsfw_channel,
        Forbidden: _on_forbidden,
        NotFound: _on_not_found,
        Exception: _on_exception,
    }

    replies: dict[type[Exception], str] = {
        errors.CommandNotFound: 'Command not found',
        errors.CommandOnCooldown: 'Command cooldown',
        errors.MaxConcurrencyReached: 'Too many instances of this command running',
        errors.MissingRole: 'Missing roles',
        errors.MissingAnyRole: 'Missing roles',
        errors.BotMissingRole: 'Bot missing roles',
        errors.BotMissingAnyRole: 'Bot missing roles',
        errors.MissingPermissions: 'Missing perms',
        errors.BotMissingPermissions: 'Bot missing perms',
        errors.CheckFailure: 'Not allowed',
        errors.CheckAnyFailure: 'Not allowed',
        errors.ArgumentParsingError: 'Parsing error',
        errors.ExpectedClosingQuoteError: 'No closing quote found',
        errors.UnexpectedQuoteError: 'Unexpected quote',
        errors.InvalidEndOfQuotedStringError: 'Missing spaces after quotes',
        errors.MissingRequiredArgument: 'Not enough arguments',
        errors.TooManyArguments: 'Too many argument',
        errors.ConversionError: 'Parsing error',
        (errors.MessageNotFound,
         errors.MemberNotFound,
         errors.UserNotFound,
         errors.ChannelNotFound,
         errors.RoleNotFound,
         errors.EmojiNotFound): 'Not found',
        errors.PartialEmojiConversionFailure: 'Emote not found',
        errors.BadInviteArgument: 'Invalid invite',
        errors.BadBoolArgument: 'Incorrect value to a true/false argument',
        errors.ChannelNotReadable: 'No access to channel',
        errors.BadColourArgument: 'Incorrect color format',
        errors.BadUnionArgument: 'Did not understand argument',
        errors.BadArgument: 'Did not understand argument',
        errors.NSFWChannelRequired: 'NSFW only',
        Forbidden: 'Forbidden by Discord',
        NotFound: 'Not found on Discord',
        Exception: 'Error',
    }

    for exc, reply in replies.items():
        if not isinstance(exc, tuple):
            exc = (exc,)
        for exc_t in exc:
            replies[exc_t] = {reply}

    for exc in ignored:
        errordict[exc] = None

    for exc, handler in handlers.items():
        if not isinstance(exc, tuple):
            exc = (exc,)
        for exc_t in exc:
            errordict[exc_t] = handler

    return Environment(errordict, replies)
