from dougbot2.blueprints import MissionControl

from .bot import Help


def setup(bot: MissionControl):
    bot.add_cog(Help(bot))
