from dougbot2.blueprints import MissionControl

from .bot import Controls


def setup(bot: MissionControl):
    bot.add_cog(Controls(bot))
