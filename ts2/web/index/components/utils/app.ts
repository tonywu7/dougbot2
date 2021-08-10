import { Component, createApp, App, onBeforeMount, onMounted } from 'vue'
import { PropSupplier } from '../../components/utils/types'

export function createAppWithDataset<T extends Component>(
    app: T,
    target: HTMLElement,
    props?: PropSupplier<T>
) {
    let dataset = { ...target.dataset, ...props }
    return createApp(app, dataset)
}

export function mountOptionalApp(
    getApp: (el: HTMLElement, ...args: any) => App,
    selector: string
) {
    let elem = document.querySelector<HTMLElement>(selector)
    if (elem) {
        return getApp(elem).mount(elem)
    }
}

export function selectAndMount<T extends Component>(
    selector: string,
    app: T,
    props?: PropSupplier<T>
) {
    return mountOptionalApp(
        (el) => createAppWithDataset(app, el, props),
        selector
    )
}
