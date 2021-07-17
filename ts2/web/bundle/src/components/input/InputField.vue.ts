import { defineComponent, computed } from 'vue'

let FORM_CONTROL_TYPES: Record<string, string> = {
    text: 'form-control',
    textarea: 'form-control',
    number: 'form-control',
    checkbox: 'form-check-input',
    radio: 'form-check-input',
}

export interface InputItemProps<T = {}> {
    id: string
    type: string
    name?: string
    label?: string
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
    },
    setup(props) {
        return {
            inputElem: FORM_CONTROL_TYPES[props.type],
        }
    },
    data() {
        let data = this.$attrs.data as FormDataType | undefined
        let initial = this.$attrs.initial as FormDataType | undefined
        data = data || initial
        return {
            _initial: initial,
            _data: data,
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
        data: {
            get(): FormDataType {
                return this.cast(this._data)
            },
            set(v: string) {
                this._data = this.cast(v)
                this.$emit('update:data', this._data)
            },
        },
        labelState(): Record<string, boolean> {
            return {
                'field-label': true,
                modified: this.data !== this.initial,
            }
        },
    },
    watch: {
        '$attrs.initial'(v) {
            this._initial = v
        },
        '$attrs.data'(v) {
            this._data = v
        },
    },
})
