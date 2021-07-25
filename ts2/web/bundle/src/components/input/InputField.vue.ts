// InputField.vue.ts
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

let FORM_CONTROL_TYPES: Record<string, string> = {
    text: 'form-control',
    textarea: 'form-control',
    number: 'form-control',
    checkbox: 'form-check-input',
    radio: 'form-check-input',
}

interface ExtraOptions {
    useSwitch: boolean
    showChanged: boolean
    [attr: string]: string | boolean
}

export interface InputItemProps {
    type: string
    id?: string
    name?: string
    label?: string
    placeholder?: string
    hint?: string
    validator?: () => string | undefined
    options?: Partial<ExtraOptions>
}

type FormDataType = string | number | boolean

export default defineComponent({
    props: {
        id: {
            type: String,
        },
        type: {
            type: String,
            required: true,
            default: 'text',
        },
        name: { type: String },
        label: {
            type: String,
            default: (props: InputItemProps) => props.name,
        },
        hint: { type: String },
        placeholder: { type: String },
        validator: {
            type: Function as PropType<(value: any) => string | undefined>,
            default: () => undefined,
        },
        options: {
            type: Object as PropType<Partial<ExtraOptions>>,
            default: {},
        },
    },
    emits: ['update:value', 'update:error'],
    setup(props) {
        return {
            inputElem: FORM_CONTROL_TYPES[props.type],
        }
    },
    data() {
        let value = this.$attrs.value as FormDataType | undefined
        let initial = this.$attrs.initial as FormDataType | undefined
        initial = initial || value
        return {
            _initial: initial,
            _value: value,
        }
    },
    methods: {
        cast(v: any): FormDataType {
            // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/NaN
            // What the actual fuck
            if (v === undefined || v === null || Number.isNaN(v)) {
                v = ''
            }
            switch (this.type) {
                case 'number':
                    return Number(v)
                case 'checkbox':
                case 'radio':
                    return Boolean(v)
                default:
                    return String(v)
            }
        },
    },
    computed: {
        initial(): FormDataType {
            return this.cast(this._initial)
        },
        value: {
            get(): FormDataType {
                return this.cast(this._value)
            },
            set(v: string) {
                this._value = this.cast(v)
                this.$emit('update:value', this._value)
            },
        },
        error(): string | undefined {
            let error = this.validator && this.validator(this.value)
            this.$emit('update:error', error)
            return error
        },
        labelState(): Record<string, boolean> {
            return {
                'field-label': true,
                modified:
                    this.options.showChanged !== false &&
                    this.value !== this.initial,
            }
        },
        containerType(): string[] {
            let classes = ['field', `field-${this.type}`]
            if (new Set(['checkbox', 'radio']).has(this.type)) {
                classes.push('form-check')
            }
            if (this.options.useSwitch) {
                classes.push('form-switch')
            }
            return classes
        },
    },
    watch: {
        '$attrs.value'(v) {
            this._value = v
        },
        '$attrs.initial'(v) {
            this._initial = v
        },
    },
})
