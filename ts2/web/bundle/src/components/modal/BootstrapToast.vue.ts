import * as bootstrap from 'bootstrap'
import { defineComponent, PropType } from 'vue'
import { Color, COLOR_CONTRAST } from './bootstrap'

export default defineComponent({
    props: {
        header: {
            type: String,
        },
        message: {
            type: String,
            required: true,
        },
        color: {
            type: String,
            required: true,
        },
        options: {
            type: Object as PropType<Partial<bootstrap.Toast.Options>>,
            default: () => ({}),
        },
        remove: {
            type: Function as PropType<() => void>,
            required: true,
        },
    },
    data() {
        let bgColor = `bg-${this.color}`
        let fg = COLOR_CONTRAST[<Color>this.color]
        let fgColor = `text-${fg}`
        let btnColor = `btn-close-${fg}`
        let theming = [bgColor, fgColor]
        return {
            theming,
            btnColor,
        }
    },
    mounted() {
        let elem = this.$refs.main as HTMLElement
        let toast = new bootstrap.Toast(elem, this.options)
        elem.addEventListener('hidden.bs.toast', () => {
            elem.remove()
            this.remove()
        })
        toast.show()
    },
})
