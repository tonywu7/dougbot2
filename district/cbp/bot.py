from ts2.discord.cog import Gear


class CBP(
    Gear, name='CBP', order=99,
    description='',
):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
