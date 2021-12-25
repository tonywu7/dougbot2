# models.py
# Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from django.db import models


class Action(models.TextChoices):
    ENABLED = 'enabled', 'Commands are enabled'
    DISABLED = 'disabled', 'Commands are disabled'


class RoleModifier(models.IntegerChoices):
    NONE = 0, 'none of'
    ANY = 1, 'any of'
    ALL = 2, 'all of'


class AccessControl(models.Model):
    server = models.ForeignKey('discord.Server', on_delete=models.CASCADE, related_name='acl')
    name: str = models.TextField()
    command: str = models.CharField(max_length=120, blank=True)
    channel: int = models.BigIntegerField()
    roles: list[int] = models.JSONField(default=list)
    modifier: int = models.IntegerField(choices=RoleModifier.choices)
    action: str = models.CharField(max_length=120, choices=Action.choices)
    error: str = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=['server_id', 'command', 'channel'],
                name='ix_acl_server_command_channel',
            ),
        ]

    def calc_specificity(self):
        return (
            int(self.modifier == 0) and len(self.roles),
            int(self.modifier == 2) and len(self.roles),
            int(self.modifier == 1) and bool(self.roles),
            (bool(self.channel) << 1) + (bool(self.command) << 0),
        )

    @property
    def enabled(self) -> bool:
        return self.action == Action.ENABLED.value
