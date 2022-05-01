from dougbot2.blueprints import MissionControl

from .bot import Internet


def setup(bot: MissionControl):
    bot.add_cog(Internet(bot))
