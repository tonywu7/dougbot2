from dougbot2.blueprints import MissionControl

from .bot import Ticker


def setup(bot: MissionControl):
    bot.add_cog(Ticker(bot))
