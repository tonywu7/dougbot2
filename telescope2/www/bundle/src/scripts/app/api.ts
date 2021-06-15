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
import { ResponsiveForm, displayNotification } from './responsive'

export type Constructor = new (...args: any[]) => {}
export type GConstructor<T = {}> = new (...args: any[]) => T

type Submissible = FormData | string
type StateChangeMethods = 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export interface AsyncPOST {
    post(): Promise<void>
}

export interface AsyncPUT {
    put(): Promise<void>
}

export interface AsyncDELETE {
    delete(): Promise<void>
}

type AsyncSubmit = GConstructor<{
    submit(data: Submissible, method: StateChangeMethods): Promise<Response | null>
}>

type FormController = GConstructor<{
    getData(): Submissible
    checkValid(): boolean
    updateDefaults(): void
}>

export function AsyncPostSubmit<TBase extends AsyncSubmit & FormController>(Base: TBase) {
    return class AsyncSubmit extends Base {
        async submit(data: Submissible, method: StateChangeMethods): Promise<Response | null> {
            let res = await super.submit(data, method)
            if (res === null) return null
            if (res.status < 299) {
                this.updateDefaults()
                let msg: string
                try {
                    msg = (await res.json()).message
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
            return res
        }
    }
}

export function SupportsPOST<TBase extends AsyncSubmit & FormController>(Base: TBase) {
    return class SupportsPOST extends Base {
        async post() {
            return await this.submit(this.getData(), 'POST')
        }
    }
}

export function SupportsPUT<TBase extends AsyncSubmit & FormController>(Base: TBase) {
    return class SupportsPOST extends Base {
        async put() {
            return await this.submit(this.getData(), 'PUT')
        }
    }
}

export function SupportsPATCH<TBase extends AsyncSubmit & FormController>(Base: TBase) {
    return class SupportsPOST extends Base {
        async patch() {
            return await this.submit(this.getData(), 'PATCH')
        }
    }
}

export function SupportsDELETE<TBase extends AsyncSubmit & FormController>(Base: TBase) {
    return class SupportsPOST extends Base {
        async delete() {
            return await this.submit(this.getData(), 'DELETE')
        }
    }
}

export class AsyncModelForm {
    readonly endpoint: string
    protected form: HTMLFormElement

    constructor(form: HTMLFormElement) {
        this.form = form
        this.endpoint = form.dataset.endpoint!
        this.initSubmitListener()
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
