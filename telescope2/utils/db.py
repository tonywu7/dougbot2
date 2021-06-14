# db.py
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

from asgiref.sync import sync_to_async
from django.db import transaction


class async_atomic:
    @sync_to_async
    def __aenter__(self):
        transaction.atomic().__enter__()

    @sync_to_async
    def __aexit__(self, exc_type, exc, tb):
        transaction.atomic().__exit__(exc_type, exc, tb)
