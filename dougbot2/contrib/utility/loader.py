from dougbot2.blueprints import MissionControl

from .bot import Utilities


def setup(bot: MissionControl):
    bot.add_cog(Utilities(bot))
