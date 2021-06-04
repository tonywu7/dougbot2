export function killAllChildren(elem: HTMLElement) {
    while (elem.firstElementChild) elem.removeChild(elem.firstElementChild)
}

export function slugify(text: string, toStrip: RegExp = /[\W_]+/g) {
    return text.replace(toStrip, ' ').trim().toLowerCase()
}

export function replaceHash(hash: string) {
    let url = new URL(window.location.toString())
    url.hash = hash
    window.history.replaceState(null, document.title, url.toString())
}

export function getOptions(hash: string): Record<string, string> {
    hash = hash.slice(1)
    if (!hash.length) return {}
    let params = hash.split(';')
    let options: Record<string, string> = {}
    for (let p of params) {
        let s = p.split('=', 2)
        if (s.length == 2) options[s[0]] = s[1]
    }
    return options
}

export function remToPx(rem: string): number {
    return parseFloat(rem) * parseFloat(getComputedStyle(document.documentElement).fontSize)
}

export function setOptions(items: Record<string, string>) {
    let options = getOptions(window.location.hash)
    Object.assign(options, items)
    window.location.hash = Object.entries(options)
        .map(([k, v]) => `${k}=${v}`)
        .join(';')
}

export function isSmallDevice() {
    return window.matchMedia('(max-width: 768px)').matches
}

export function doesNotSupportHover() {
    return !window.matchMedia('(hover: hover)').matches
}

export function hasCoarsePointer() {
    return window.matchMedia('(pointer: coarse)').matches
}

export function dropdownTitle(text: string) {
    let title = document.createElement('h6')
    title.classList.add('dropdown-header')
    title.textContent = text
    return title
}

export function dropdownItem<K extends keyof HTMLElementTagNameMap>(elem: K) {
    let e = document.createElement(elem)
    e.classList.add('dropdown-item')
    return e
}

export function dropdownAnchor(href: string, text: string | HTMLElement) {
    let anchor: HTMLAnchorElement = dropdownItem('a')
    anchor.href = href
    if (text instanceof HTMLElement) {
        anchor.appendChild(text)
    } else {
        anchor.textContent = text
    }
    return anchor
}

export function cloneNode<T extends Node>(node: T, arg: boolean = true): T {
    return node.cloneNode(arg) as T
}

export function getTemplate(id: string, rootElement: string): HTMLElement {
    return cloneNode((document.querySelector(`template#${id}`) as HTMLTemplateElement).content).querySelector(
        rootElement
    ) as HTMLElement
}

export function chain<T>(iterables: Iterable<T>[]): Iterator<T, any, undefined> {
    let pointer = 0
    let iter: Iterator<T, any, undefined> | undefined = undefined
    return {
        next: () => {
            while (true) {
                let nextItem = iter?.next()
                if (!nextItem || nextItem.done) {
                    let iterator = iterables[pointer++]
                    if (!iterator) return { done: true, value: undefined }
                    iter = iterator[Symbol.iterator]() as Iterator<T, any, undefined>
                } else {
                    return nextItem
                }
            }
        },
    }
}

export function deferredEventHandler(s: number, handler: (...args: any) => void) {
    let changing: number
    return () => {
        clearTimeout(changing)
        changing = window.setTimeout(() => handler(...arguments), s)
    }
}

export function fisherYatesShuffle<T>(items: T[]): void {
    for (let i = items.length - 1; i >= 0; i--) {
        let r = Math.floor(Math.random() * i + 1)
        let t: T = items[i]
        items[i] = items[r]
        items[r] = t
    }
}
