from dougbot2.blueprints import MissionControl

from .bot import Museum


def setup(bot: MissionControl):
    bot.add_cog(Museum(bot))
