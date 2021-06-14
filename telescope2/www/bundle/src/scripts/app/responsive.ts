// responsive.ts
// Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

import * as bootstrap from 'bootstrap'
import * as Mustache from 'mustache'

export class ResponsiveForm {
    form: HTMLFormElement

    constructor(form: HTMLFormElement) {
        this.form = form
        this.initListeners()
    }

    protected initListeners() {
        for (let input of this.form.querySelectorAll('input')) {
            input.addEventListener('input', this.createInputListener(input))
        }
    }

    protected createInputListener(input: HTMLInputElement): (ev: Event) => void {
        let labels = input.labels
        let changed: () => boolean
        if (input.type === 'checkbox') {
            changed = () => input.defaultChecked != input.checked
        } else {
            changed = () => input.defaultValue != input.value
        }
        return (ev) => {
            input.setCustomValidity('')
            if (changed()) {
                labels?.forEach((label) => label.classList.add('input-changed'))
                input.classList.add('input-changed')
            } else {
                labels?.forEach((label) => label.classList.remove('input-changed'))
                input.classList.remove('input-changed')
            }
        }
    }

    public checkValid(): boolean {
        let valid = this.form.checkValidity()
        if (!valid) {
            this.form.reportValidity()
        }
        return valid
    }

    public async submit() {
        if (!this.checkValid()) return
        this.form.submit()
    }
}

export class TemplateRenderer {
    private templates: Record<string, string> = {}

    constructor(container: HTMLElement) {
        container.querySelectorAll('.handlebars-template').forEach((e) => {
            let elem = (e as HTMLTemplateElement).content.firstElementChild!
            this.templates[e.id] = elem.outerHTML
        })
    }

    public render(id: string, context: Record<string, any>): HTMLElement {
        let template = this.templates[id]
        let parser = document.createElement('template')
        let rendered = Mustache.render(template, context).trim()
        parser.innerHTML = rendered
        return parser.content.firstElementChild as HTMLElement
    }
}

export function displayNotification(notif: HTMLElement, options?: Partial<bootstrap.Toast.Options>) {
    let toast = new bootstrap.Toast(notif, options)
    let center = document.querySelector('#toast-container') as HTMLElement
    notif.addEventListener('hidden.bs.toast', () => {
        notif.remove()
    })
    center.appendChild(notif)
    toast.show()
}

export class D3ItemList {
    container: HTMLElement

    input: HTMLInputElement
    field: HTMLElement

    userEntry: HTMLInputElement

    dropdownToggle: HTMLElement
    dropdownMenu: HTMLElement
    dropdown: bootstrap.Dropdown

    itemList: HTMLUListElement

    constructor(container: HTMLElement) {
        this.container = container

        this.input = container.querySelector('input[data-target]') as HTMLInputElement
        this.field = container.querySelector('.form-control') as HTMLElement

        this.userEntry = this.field.querySelector('input[type="text"]') as HTMLInputElement

        this.dropdownToggle = container.querySelector('[data-bs-toggle="dropdown"]') as HTMLElement
        this.dropdownMenu = container.querySelector('.dropdown') as HTMLElement
        this.dropdown = new bootstrap.Dropdown(this.dropdownToggle)

        this.itemList = this.dropdownMenu.querySelector('ul') as HTMLUListElement

        this.addListeners()
    }

    private addListeners() {
        this.container.addEventListener('focusout', () => this.dropdown.hide())
        this.userEntry.addEventListener('focus', () => this.dropdown.show())
        this.userEntry.addEventListener('focus', () => this.resetHighlight.bind(this))
        this.container.addEventListener('keydown', this.keyboardListener.bind(this))
    }

    public get expanded(): boolean {
        return this.itemList.classList.contains('show')
    }

    protected keyboardListener(ev: KeyboardEvent): void {
        if (!this.expanded) return
        if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
            return this.moveItemHighlight(ev.key)
        } else if (ev.key === 'Enter') {
            return this.selectItem()
        } else if (ev.key === 'Escape') {
            return this.blur()
        }
    }

    protected resetHighlight(key: string) {
        this.itemList.querySelectorAll('.item-selected').forEach((elem) => {
            elem.classList.remove('item-selected')
        })
    }

    protected moveItemHighlight(key: string) {
        let focused = this.itemList.querySelector('.item-selected')
        let terminalElem: keyof HTMLUListElement
        let nextElem: keyof HTMLElement
        if (key === 'ArrowDown') {
            terminalElem = 'firstElementChild'
            nextElem = 'nextElementSibling'
        } else if (key === 'ArrowUp') {
            terminalElem = 'lastElementChild'
            nextElem = 'previousElementSibling'
        } else {
            return
        }
        if (focused === null) {
            this.itemList[terminalElem]?.classList.add('item-selected')
        } else {
            let nextItem = focused[nextElem]
            if (nextItem !== null) {
                nextItem.classList.add('item-selected')
                focused.classList.remove('item-selected')
            }
        }
    }

    protected selectItem() {
        this.itemList.querySelector('.item-selected')?.dispatchEvent(new Event('click', { bubbles: true }))
    }

    protected blur() {
        this.userEntry.blur()
    }
}
