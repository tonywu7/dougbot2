from dougbot2.blueprints import MissionControl
from dougbot2.utils.english import NP

from .bot import Debug
from .converters import LoggingLevel


def setup(bot: MissionControl):
    bot.manpage.register_type(LoggingLevel, NP('logging level name', concise='logging level'))
    bot.add_cog(Debug(bot))
