// InputSelect.vue.ts
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

import { defineComponent, PropType } from 'vue'

export interface InputSelectOption<T = any> {
    value: T
    text: string
}

export default defineComponent({
    props: {
        id: String,
        label: String,
        options: {
            type: Object as PropType<InputSelectOption[]>,
            required: true,
        },
        initial: [String, Number, Boolean],
    },
    emits: ['update:value'],
    data() {
        return { _value: this.initial || this.options[0].value }
    },
    computed: {
        choices(): Record<string, InputSelectOption> {
            return Object.assign(
                {},
                ...this.options.map((d) => ({ [d.value.toString()]: d }))
            )
        },
        display(): string {
            let choice = this.choices[this._value]
            let text: string
            if (choice === undefined) {
                text = '(no selection)'
            } else {
                text = choice.text
            }
            return text
        },
    },
    watch: {
        _value(v) {
            this.$emit('update:value', this._value)
        },
        '$attrs.value': {
            handler(v) {
                this._value = v
            },
            immediate: true,
        },
    },
})
