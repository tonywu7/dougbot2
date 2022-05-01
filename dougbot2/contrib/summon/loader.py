from dougbot2.blueprints import MissionControl

from .bot import Summon


def setup(bot: MissionControl):
    bot.add_cog(Summon(bot))
