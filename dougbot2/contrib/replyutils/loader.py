from dougbot2.blueprints import MissionControl
from dougbot2.utils.memo import get_memo

from .bot import ReplyUtils


def setup(bot: MissionControl):
    bot.add_cog(ReplyUtils(bot))

    def deferred():
        for cmd in bot.walk_commands():
            memo = get_memo(cmd, '__reply_utils__', '_callback', default=[])
            for func in reversed(memo):
                func(cmd)
    bot.defer_init(deferred)
