# MIT License
#
# Copyright (c) 2021 @tonyzbf +https://github.com/tonyzbf/
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from discord import Forbidden, NotFound
from discord.abc import GuildChannel
from discord.ext.commands import Context, errors
from discord.utils import escape_markdown

from ...utils.markdown import code, strong, tag_literal
from . import exceptions
from .documentation import readable_perm_name
from .errorhandling import (append_matching_quotes_hint, append_quotation_hint,
                            explains, prepend_argument_hint)
from .lang import (describe_concurrency, indicate_eol, indicate_extra_text,
                   pl_cat_attributive)


def _format_roles(roles: list[int]):
    return pl_cat_attributive('role', [tag_literal('role', r) for r in roles], conj='or')


def _format_permissions(perms: list[str]):
    return pl_cat_attributive('permission', [strong(readable_perm_name(p)) for p in perms])


@explains(exceptions.ReplyRequired, 'Message reference required', priority=5)
async def explains_required_reply(ctx, exc) -> tuple[str, int]:
    return str(exc), 20


@explains(exceptions.NotAcceptable, 'Input not acceptable', priority=5)
async def explains_not_acceptable(ctx, exc) -> tuple[str, int]:
    return str(exc), 60


@explains(errors.CommandOnCooldown, 'Command on cooldown', 0)
async def on_cooldown(ctx, exc: errors.CommandOnCooldown):
    cooldown = exc.cooldown.per
    try:
        from pendulum import duration
    except ModuleNotFoundError:
        cooldown_words = f'{cooldown:.0f}s'
        retry_words = f'{exc.retry_after:.0f}s'
    else:
        cooldown_words = duration(seconds=cooldown).in_words()
        retry_words = duration(seconds=exc.retry_after).in_words()
    return (
        f'This command has a cooldown of {cooldown_words}\n'
        f'Try again in {retry_words}'
    ), 10


@explains(errors.MaxConcurrencyReached, 'Too many instances of this command running', 0)
async def on_max_concurrent(ctx, exc):
    return f'This command allows {describe_concurrency(exc.number, exc.per)}', 10


@explains(errors.MissingRole, 'Missing roles', 0)
async def on_missing_role(ctx, exc):
    explanation = f'You are missing the {tag_literal("role", exc.missing_role)} role.'
    return explanation, 30


@explains(errors.MissingAnyRole, 'Missing roles', 0)
async def on_missing_any_role(ctx, exc: errors.MissingAnyRole):
    roles = _format_roles(exc.missing_roles)
    explanation = f'You are missing the {roles}.'
    return explanation, 30


@explains(errors.BotMissingRole, 'Bot missing roles', 0)
async def on_bot_missing_role(ctx, exc: errors.MissingAnyRole):
    explanation = (f'The bot is missing the {tag_literal("role", exc.missing_role)}'
                   ' required to run this command.')
    return explanation, 30


@explains(errors.BotMissingAnyRole, 'Bot missing roles', 0)
async def on_bot_missing_any_role(ctx, exc: errors.BotMissingAnyRole):
    roles = _format_roles(exc.missing_roles)
    explanation = (f'The bot is missing the {roles}'
                   ' required to run this command.')
    return explanation, 30


@explains(errors.NotOwner, 'Not owner', priority=100)
async def on_not_owner(ctx, exc):
    return False


@explains(errors.MissingPermissions, 'Missing perms', 0)
async def on_missing_perms(ctx, exc: errors.MissingPermissions):
    perms = _format_permissions(exc.missing_perms)
    try:
        channel: GuildChannel = getattr(exc, 'channel')
    except AttributeError:
        where = ''
    else:
        where = f' in {channel.mention}'
    explanation = f'You are missing the {perms}{where}.'
    return explanation, 20


@explains(errors.BotMissingPermissions, 'Bot missing perms', 0)
async def on_bot_missing_perms(ctx, exc: errors.BotMissingPermissions):
    perms = _format_permissions(exc.missing_perms)
    try:
        channel: GuildChannel = getattr(exc, 'channel')
    except AttributeError:
        where = ''
    else:
        where = f' in {channel.mention}'
    explaination = (f'The bot is missing the {perms}{where}'
                    f' required to run this command.')
    return explaination, 60


@explains(errors.CheckFailure, 'Not allowed', -10)
async def on_generic_check_failure(ctx, exc):
    return 'You are not allowed to use this command.', 20


@explains(errors.CheckAnyFailure, 'Not allowed', -10)
async def on_check_any_failure(ctx, exc: errors.CheckAnyFailure):
    reasons = '\n'.join([f'- {e}' for e in exc.errors])
    return f'You are not allowed to use this command:\n{reasons}', 20


@explains(errors.NoPrivateMessage, 'Only in a server', -10)
@explains(errors.PrivateMessageOnly, 'Only in DMs', -10)
async def on_wrong_context(ctx, exc):
    return False


@explains(errors.ArgumentParsingError, 'Parsing error', -10)
async def on_generic_parsing_error(ctx, exc):
    return 'Error while parsing the command.', 20


@explains(errors.ExpectedClosingQuoteError, 'No closing quote found')
async def on_unexpected_eof(ctx, exc: errors.ExpectedClosingQuoteError):
    return (f'Expected another {code(exc.close_quote)} at the end. '
            'Make sure your opening and closing quotes match.'), 60


@explains(errors.UnexpectedQuoteError, 'Unexpected quote')
@append_matching_quotes_hint()
async def on_unexpected_quote(ctx, exc: errors.UnexpectedQuoteError):
    return f'\n> {indicate_eol(ctx.view)} ⚠️ Did not expect a {code(exc.quote)} here', 60


@explains(errors.InvalidEndOfQuotedStringError, 'Missing spaces after quotes')
@append_matching_quotes_hint()
async def on_unexpected_char_after_quote(ctx, exc: errors.InvalidEndOfQuotedStringError):
    return (f'\n> {indicate_eol(ctx.view)} ⚠️ There should be a space before this '
            f'character {code(exc.char)} after the quote.'), 60


@explains(errors.MissingRequiredArgument, 'Not enough arguments')
@prepend_argument_hint(sep='\n⚠️ ')
async def on_missing_args(ctx, exc):
    return 'This argument is missing.', 60


@explains(errors.TooManyArguments, 'Too many arguments')
@append_quotation_hint()
async def on_too_many_args(ctx, exc: errors.TooManyArguments):
    return f'\n> {indicate_extra_text(ctx.view)} ⚠️ {strong("Unrecognized argument found.")}', 60


@explains(errors.ConversionError, 'Parsing error', -10)
@prepend_argument_hint(sep='\n⚠️ ')
async def on_generic_conversion_error(ctx, exc: Exception):
    if exc.__cause__:
        return f'Error while parsing this argument: {exc.__cause__}', 30
    return 'Error while parsing this argument.', 20


@explains((
    errors.MessageNotFound,
    errors.MemberNotFound,
    errors.UserNotFound,
    errors.ChannelNotFound,
    errors.RoleNotFound,
    errors.EmojiNotFound,
), 'Not found', priority=5)
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_not_found(ctx: Context, exc) -> tuple[str, int]:
    return escape_markdown(str(exc)), 30


@explains(errors.PartialEmojiConversionFailure, 'Emote not found', priority=5)
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_emote_not_found(ctx: Context, exc: errors.PartialEmojiConversionFailure) -> tuple[str, int]:
    return f'{escape_markdown(exc.argument)} is not an emote or is not in a valid Discord emote format.', 30


@explains(errors.BadInviteArgument, 'Invalid invite')
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_bad_invite(ctx: Context, exc: errors.BadInviteArgument) -> tuple[str, int]:
    return strong(escape_markdown(str(exc))), 30


@explains(errors.BadBoolArgument, 'Incorrect value to a true/false argument')
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_bad_boolean(ctx: Context, exc: errors.BadBoolArgument) -> tuple[str, int]:
    return (
        (strong(escape_markdown(exc.argument))
         + ' is not an acceptable answer to a true/false question in English.\n\n')
        + ('The following are considered to be true: '
           'yes, y, true, t, 1, enable, on\n'
           'The following are considered to be false: '
           'no, n, false, f, 0, disable, off')
    ), 60


@explains(errors.ChannelNotReadable, 'No access to channel')
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_channel_not_readable(ctx: Context, exc) -> tuple[str, int]:
    return escape_markdown(str(exc)), 30


@explains(errors.BadColourArgument, 'Incorrect color format', priority=5)
@prepend_argument_hint(sep='\n⚠️ ')
async def explains_bad_color(ctx: Context, exc: errors.BadColourArgument) -> tuple[str, int]:
    example = code('"rgb(255, 255, 255)"')
    return (f'{strong(escape_markdown(str(exc)))}\n\nTo provide a color in the RGB format that also contains '
            f'spaces, be sure to quote it in double quotes: {example}'), 30


@explains(errors.BadUnionArgument, 'Did not understand argument', 0)
@prepend_argument_hint(sep='\n⚠️ ', include_types=True)
async def on_bad_union(ctx, exc: errors.BadUnionArgument):
    return 'Could not recognize this argument as any of the above.', 45


@explains(errors.BadArgument, 'Did not understand argument', -1)
@prepend_argument_hint(sep='\n⚠️ ')
async def on_bad_args(ctx, exc):
    return escape_markdown(str(exc)), 30


@explains(errors.CommandNotFound, 'Command not found', -10)
async def on_cmd_not_found(ctx: Context, exc: errors.CommandNotFound):
    return False


@explains(errors.NSFWChannelRequired, 'NSFW-only')
async def on_nsfw_channel_required(ctx, exc):
    return 'This command must only be used in a NSFW channel.', 20


@explains(Forbidden, 'Forbidden by Discord', 0)
async def on_forbidden(ctx, exc):
    return ("The bot doesn't have the necessary server/channel permission"
            f' to finish the command: {exc}'), 20


@explains(NotFound, 'Not found on Discord', 0)
async def on_not_found(ctx, exc: NotFound):
    return f"Discord can't find the requested info: {exc}", 30


@explains(Exception, 'Error', -100)
async def on_exception(ctx, exc):
    return 'Error while processing the command.', 20
