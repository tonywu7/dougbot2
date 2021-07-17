export function killAllChildren(elem: HTMLElement) {
    while (elem.firstElementChild) elem.removeChild(elem.firstElementChild)
}

export function cloneNode<T extends Node>(node: T, arg: boolean = true): T {
    return node.cloneNode(arg) as T
}

export function getTemplate(id: string, rootElement: string): HTMLElement {
    return cloneNode(
        document.querySelector<HTMLTemplateElement>(`template#${id}`)!.content
    ).querySelector(rootElement) as HTMLElement
}
