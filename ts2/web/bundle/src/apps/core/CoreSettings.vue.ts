import { defineComponent } from 'vue'

import InputField from '../../components/input/InputField.vue'
import FormContainer from '../../components/input/FormContainer.vue'

interface ComponentData {
    original: string
    value: string
    error?: string
}

export default defineComponent({
    components: { FormContainer, InputField },
    props: {
        prefix: { type: String, required: true },
    },
    data(): ComponentData {
        return {
            original: this.prefix,
            value: this.prefix,
            error: undefined,
        }
    },
    computed: {
        buttonState(): Record<string, boolean> {
            return { disabled: !!this.error }
        },
    },
    methods: {
        submit() {
            console.log(this.value)
        },
        validate(v: string): string | undefined {
            if (!v || !v.length) {
                return 'Prefix cannot be empty.'
            }
        },
    },
})
