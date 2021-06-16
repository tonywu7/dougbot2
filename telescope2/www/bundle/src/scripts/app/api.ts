// api.ts
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

import { renderer } from './main'
import { displayNotification, AsyncPostSubmit, ResponsiveForm } from './responsive'

export class AsyncModelForm {
    readonly endpoint: string
    protected form: HTMLFormElement

    constructor(form: HTMLFormElement) {
        this.form = form
        this.endpoint = form.dataset.endpoint!
        this.initLabelListeners()
        this.initSubmitListener()
    }

    protected initLabelListeners() {
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

    protected initSubmitListener() {
        let button = this.form.querySelector('.async-form-submit') as HTMLButtonElement
        if (button === null) return
        button.addEventListener('click', async () => {
            await this.submit(this.getData(), 'POST')
        })
    }

    private getCSRF(): string {
        let csrf = this.form.querySelector('input[type="hidden"][name="csrfmiddlewaretoken"]') as HTMLInputElement
        if (csrf === null) {
            throw new Error(`No CSRF token found for form ${this.form}`)
        }
        return csrf.value
    }

    updateDefaults() {
        this.form.querySelectorAll('input').forEach((input) => {
            input.defaultChecked = input.checked
            input.defaultValue = input.value
            input.dispatchEvent(new Event('input'))
        })
        this.checkValid()
    }

    checkValid(): boolean {
        let valid = this.form.checkValidity()
        if (!valid) {
            this.form.reportValidity()
        }
        return valid
    }

    getData(): FormData {
        return new FormData(this.form)
    }

    public async submit(data: FormData, method = 'POST') {
        if (!this.checkValid()) return null
        try {
            let options: RequestInit = {
                method: method,
                mode: 'same-origin',
                body: data,
                headers: {
                    'X-CSRFToken': this.getCSRF(),
                },
            }
            if (typeof data === 'string') {
                ;(options.headers as any)['Content-Type'] = 'application/json'
            }
            return await fetch(this.endpoint, options)
        } catch (e) {
            let notif = renderer.render('async-form-update-error', { error: 'Cannot connect to server' })
            displayNotification(notif, { autohide: false, delay: 20 })
            return null
        }
    }
}

export const AsyncResponsiveModelForm = AsyncPostSubmit(AsyncModelForm)

export function getCSRF(elem: HTMLElement) {
    let csrf = elem.querySelector('input[type="hidden"][name="csrfmiddlewaretoken"]') as HTMLInputElement
    if (csrf === null) {
        throw new Error(`No CSRF token found for form ${elem}`)
    }
    return csrf.value
}
