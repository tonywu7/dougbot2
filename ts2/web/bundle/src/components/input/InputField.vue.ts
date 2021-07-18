import { defineComponent, computed, PropType } from 'vue'

let FORM_CONTROL_TYPES: Record<string, string> = {
    text: 'form-control',
    textarea: 'form-control',
    number: 'form-control',
    checkbox: 'form-check-input',
    radio: 'form-check-input',
}

export interface InputItemProps {
    id: string
    type: string
    name?: string
    label?: string
    hint?: string
}

type FormDataType = string | number | boolean

export default defineComponent({
    props: {
        id: {
            type: String,
            required: true,
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
        validator: {
            type: Function as PropType<(value: any) => string | undefined>,
            default: () => undefined,
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
        setInitial(v: any) {
            this._initial = v
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
                modified: this.value !== this.initial,
            }
        },
    },
    watch: {
        '$attrs.value'(v) {
            this._value = v
        },
    },
})
