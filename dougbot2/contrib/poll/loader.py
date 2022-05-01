from dougbot2.blueprints import MissionControl

from .bot import Polling


def setup(bot: MissionControl):
    bot.add_cog(Polling(bot))
