import { defineComponent } from 'vue'

import InputField from '../../components/input/InputField.vue'
import FormContainer from '../../components/input/FormContainer.vue'

import { server } from '../../server'
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'
import { ApolloError } from '@apollo/client/errors'

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
        async submit() {
            try {
                await server.setPrefix(this.value)
                ;(this.$refs.input as typeof InputField).reset()
                displayNotification(Color.SUCCESS, 'Settings updated.')
            } catch (e) {
                let err = e as ApolloError
                displayNotification(
                    Color.DANGER,
                    err.message,
                    'Error saving settings',
                    {
                        autohide: false,
                    }
                )
            }
        },
        validate(v: string): string | undefined {
            if (!v || !v.length) {
                return 'Prefix cannot be empty.'
            }
        },
    },
})
