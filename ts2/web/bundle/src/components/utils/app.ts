import { Component, createApp, App } from 'vue'

export function createAppWithDataset<T extends Component>(
    app: T,
    target: HTMLElement
) {
    let props = { ...target.dataset }
    return createApp(app, props)
}

export function mountOptionalApp(
    getApp: (el: HTMLElement) => App,
    selector: string
) {
    let elem = document.querySelector<HTMLElement>(selector)
    if (elem) {
        return getApp(elem).mount(elem)
    }
}

export function selectAndMount<T extends Component>(selector: string, app: T) {
    return mountOptionalApp((el) => createAppWithDataset(app, el), selector)
}
