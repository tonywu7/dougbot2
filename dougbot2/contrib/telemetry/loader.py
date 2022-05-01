from dougbot2.blueprints import MissionControl

from .bot import Telemetry


def setup(bot: MissionControl):
    bot.add_cog(Telemetry(bot))
