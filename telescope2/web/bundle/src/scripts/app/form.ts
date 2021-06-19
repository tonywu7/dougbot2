// form.ts
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
import { displayNotification } from './responsive'

export class ResponsiveForm {
    protected _form?: HTMLFormElement

    constructor(form?: HTMLFormElement) {
        this._form = form
        this.initLabelListeners()
    }

    protected get form(): HTMLFormElement | undefined {
        return this._form
    }

    protected initLabelListeners() {
        for (let input of this.form?.querySelectorAll('input') || []) {
            input.addEventListener('input', this.createLabelListener(input))
            input.addEventListener('change', this.createLabelListener(input))
        }
    }

    protected createLabelListener(input: HTMLInputElement): (ev: Event) => void {
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

    public checkValidity(): boolean {
        let valid = this.form?.checkValidity()
        if (!valid) {
            this.form?.reportValidity()
        }
        return valid || false
    }

    public async submit(): Promise<any> {
        if (!this.checkValidity()) return
        this.form?.submit()
    }
}

export class AsyncModelForm extends ResponsiveForm {
    protected endpoint?: string

    constructor(form?: HTMLFormElement) {
        super(form)
        this.endpoint = this.form?.dataset.endpoint
        this.initSubmitListener()
    }

    protected initSubmitListener() {
        let button = this.form?.querySelector('.async-form-submit') as HTMLButtonElement
        if (!button) return
        button.addEventListener('click', async () => {
            await this.submit()
        })
    }

    protected getCSRF(): string {
        let csrf = this.form?.querySelector('input[type="hidden"][name="csrfmiddlewaretoken"]') as HTMLInputElement
        if (!csrf) {
            throw new Error(`No CSRF token found for form ${this.form}`)
        }
        return csrf.value
    }

    protected requestInit(): RequestInit {
        return {
            method: 'POST',
            mode: 'same-origin',
            body: this.getData(),
            headers: {
                'X-CSRFToken': this.getCSRF(),
            },
        }
    }

    updateDefaults() {
        this.form?.querySelectorAll('input').forEach((input) => {
            input.defaultChecked = input.checked
            input.defaultValue = input.value
            input.dispatchEvent(new Event('input'))
        })
        this.checkValidity()
    }

    checkValidity(): boolean {
        let valid = this.form?.checkValidity()
        if (!valid) {
            this.form?.reportValidity()
        }
        return valid || false
    }

    getData() {
        return new FormData(this.form)
    }

    protected async postSubmit(response: Response | null): Promise<Response | null> {
        if (!response) return null
        let res = response.clone()
        if (res.status < 299) {
            this.updateDefaults()
            let msg: string
            try {
                msg = (await res.json()).message || 'Settings saved.'
            } catch (e) {
                switch (res.status) {
                    case 204:
                        msg = 'Settings saved.'
                        break
                    case 201:
                        msg = 'Items created'
                        break
                    default:
                        msg = 'Submission accepted'
                        break
                }
            }
            let notif = renderer.render('async-form-update-successful', { message: msg })
            displayNotification(notif)
        } else {
            let msg: string
            try {
                let data = await res.json()
                msg = data.error
            } catch (e) {
                msg = `Server error; status ${res.status}`
            }
            let notif = renderer.render('async-form-update-error', { error: msg })
            displayNotification(notif, { autohide: false, delay: 20 })
        }
        return response
    }

    protected async post(): Promise<Response | null> {
        if (!this.checkValidity()) return null
        if (!this.endpoint) return null
        try {
            let options: RequestInit = this.requestInit()
            return await fetch(this.endpoint, options)
        } catch (e) {
            let notif = renderer.render('async-form-update-error', { error: 'Cannot connect to server' })
            displayNotification(notif, { autohide: false, delay: 20 })
            return null
        }
    }

    public async submit() {
        let res = await this.post()
        return await this.postSubmit(res)
    }
}

export function getCSRF(elem: HTMLElement) {
    let csrf = elem.querySelector('input[type="hidden"][name="csrfmiddlewaretoken"]') as HTMLInputElement
    if (!csrf) {
        throw new Error(`No CSRF token found for form ${elem}`)
    }
    return csrf.value
}
