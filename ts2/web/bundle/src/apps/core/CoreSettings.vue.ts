import { defineComponent } from 'vue'

import InputField from '../../components/input/InputField.vue'
import FormContainer from '../../components/input/FormContainer.vue'

export default defineComponent({
    components: { FormContainer, InputField },
    props: {
        prefix: { type: String, required: true },
    },
    data() {
        return {
            original: this.prefix,
            value: this.prefix,
        }
    },
})
