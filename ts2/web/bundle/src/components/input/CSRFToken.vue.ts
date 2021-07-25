import { defineComponent } from 'vue'
import { getCSRF } from '../../utils/site'

export default defineComponent({
    data() {
        return { token: getCSRF(document.documentElement) }
    },
})
