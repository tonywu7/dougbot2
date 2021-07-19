import { defineComponent } from 'vue'

import InputField from '../../components/input/InputField.vue'
import FormContainer from '../../components/input/FormContainer.vue'

import { server } from '../../server'
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'

interface ComponentData {
    original: string
    value: string
    error?: string
    processing: boolean
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
            processing: false,
        }
    },
    computed: {
        buttonState(): Record<string, boolean> {
            return { disabled: this.processing || Boolean(this.error) }
        },
    },
    methods: {
        async submit() {
            this.processing = true
            try {
                await server.setPrefix(this.value)
            } catch (e) {
                this.processing = false
                return
            }
            ;(this.$refs.input as typeof InputField).reset()
            displayNotification(Color.SUCCESS, 'Settings updated.')
            this.processing = false
        },
        validate(v: string): string | undefined {
            if (!v || !v.length) {
                return 'Prefix cannot be empty.'
            }
        },
    },
})
