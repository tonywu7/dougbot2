import { defineComponent } from 'vue'

import InputField from '../../components/input/InputField.vue'

export default defineComponent({
    components: { InputField },
    data() {
        return {
            original: '',
            value: '',
        }
    },
    computed: {
        prefix(): string {
            return this.value
        },
    },
})
