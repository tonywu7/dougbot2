import { createApp, App } from 'vue'
import { Color } from '../modal/bootstrap'
import BootstrapToast from '../modal/BootstrapToast.vue'
import { Toast } from 'bootstrap'

export function displayNotification(
    color: Color,
    message: string,
    header?: string,
    options?: Partial<Toast.Options>
) {
    let elem = document.createElement('div')
    let app: App
    let remove = () => {
        app.unmount()
    }
    app = createApp(BootstrapToast, {
        header: header,
        message: message,
        color: color,
        options: options,
        remove: remove,
    })
    app.mount(elem)
}
