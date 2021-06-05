# utils.py
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

from typing import List, Tuple, Type

from django.contrib.admin import ModelAdmin
from django.db.models import Model


class AdminRegistrar:
    def __init__(self):
        self.queue: List[Tuple[Type[Model], Type[ModelAdmin]]] = []

    def register(self, *models):
        def wrapper(model_admin):
            for m in models:
                self.queue.append((m, model_admin))
            return model_admin
        return wrapper

    def apply_all(self, admin_site):
        for model, admin in self.queue:
            admin_site.register(model, admin)
