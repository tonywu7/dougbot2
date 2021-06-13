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
