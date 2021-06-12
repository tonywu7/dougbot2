# entity.py
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

from polymorphic.admin import (PolymorphicChildModelFilter,
                               PolymorphicParentModelAdmin)

from admin2017.models import AdminController
from admin2017.utils.inspect import polymorphic_subclasses

from ...models import Entity


class EntityRootAdmin(AdminController, PolymorphicParentModelAdmin):
    base_model = Entity
    child_models = tuple(polymorphic_subclasses(Entity))
    list_filter = [PolymorphicChildModelFilter]
