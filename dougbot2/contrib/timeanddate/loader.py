from dougbot2.blueprints import MissionControl

from .bot import TimeandDate


def setup(bot: MissionControl):
    bot.add_cog(TimeandDate(bot))
