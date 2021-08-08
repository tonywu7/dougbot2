from . import explanations
from .decorators import (accepts, accepts_reply, argument, concurrent,
                         cooldown, description, discussion, example, hidden,
                         invocation, restriction, use_syntax_whitelist)
from .documentation import Documentation, readable_perm_name
from .errorhandling import add_error_names, explain_exception, explains
from .exceptions import NoSuchCommand, NotAcceptable, ReplyRequired, SendHelp
from .manual import Manual, init_bot, set_manual_getter

explanations = explanations

__all__ = [
    'example',
    'description',
    'discussion',
    'argument',
    'invocation',
    'use_syntax_whitelist',
    'restriction',
    'hidden',
    'cooldown',
    'concurrent',
    'accepts_reply',
    'accepts',
    'SendHelp',
    'NotAcceptable',
    'NoSuchCommand',
    'ReplyRequired',
    'Manual',
    'Documentation',
    'explains',
    'explain_exception',
    'set_manual_getter',
    'init_bot',
    'readable_perm_name',
    'add_error_names',
]
