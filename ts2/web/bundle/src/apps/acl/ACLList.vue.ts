// ACLList.vue.ts
// Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import { defineComponent } from 'vue'
import InputSelect from '../../components/input/InputSelect.vue'
import { InputSelectOption } from '../../components/input/InputSelect.vue'

export default defineComponent({
    components: { InputSelect },
    data() {
        let options: InputSelectOption[] = [
            { value: 0, text: 'none of' },
            { value: 1, text: 'any of' },
        ]
        return {
            options,
            value: undefined,
        }
    },
})
