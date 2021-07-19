import { defineComponent } from 'vue'

import InputField from '../../components/input/InputField.vue'
import FormContainer from '../../components/input/FormContainer.vue'
import { server } from '../../server'
import { Color } from '../../components/modal/bootstrap'
import { displayNotification } from '../../components/utils/modal'

type ExtensionInfo = {
    id: string
    label: string
    enabled: boolean
}

export default defineComponent({
    components: { FormContainer, InputField },
    props: {
        datasrc: {
            type: String,
            required: true,
        },
    },
    setup(props) {
        let extensionElem = document.querySelector<HTMLElement>(props.datasrc)!
        let extensions: ExtensionInfo[] = []
        let values: Record<string, boolean> = {}
        extensionElem
            .querySelectorAll<HTMLElement>('.extension-label')
            .forEach((e) => {
                let id = e.dataset.id!
                let enabled = Boolean(e.dataset.enabled)
                let label = e.innerHTML
                extensions.push({ id, label, enabled })
                values[id] = enabled
            })
        return {
            extensions,
            values,
            initial: { ...values },
        }
    },
    data() {
        return {
            processing: false,
        }
    },
    methods: {
        getSubmittedValue(): string[] {
            return Object.entries(this.values)
                .filter(([k, v]) => v)
                .map(([k, v]) => k)
        },
        reset() {
            for (let [k, v] of Object.entries(this.values)) {
                this.initial[k] = v
            }
        },
        async submit() {
            this.processing = true
            try {
                await server.setExtensions(this.getSubmittedValue())
            } catch (e) {
                this.processing = false
                return
            }
            this.reset()
            displayNotification(Color.SUCCESS, 'Settings updated.')
            this.processing = false
        },
    },
})
