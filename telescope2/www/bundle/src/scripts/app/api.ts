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

export class AsyncForm extends ResponsiveForm {
    readonly endpoint: string
    private readonly csrf: string

    constructor(form: HTMLFormElement) {
        super(form)
        this.endpoint = form.dataset.endpoint!
        this.csrf = this.getCSRF()
        this.initSubmitListener()
    }

    protected initSubmitListener() {
        let button = this.form.querySelector('.async-form-submit') as HTMLButtonElement
        button.addEventListener('click', async () => {
            await this.submit()
        })
    }

    private getCSRF(): string {
        let csrf = this.form.querySelector('input[type="hidden"][name="csrfmiddlewaretoken"]') as HTMLInputElement
        if (csrf === null) {
            throw new Error(`No CSRF token found for form ${this.form}`)
        }
        return csrf.value
    }

    public updateDefaults() {
        this.form.querySelectorAll('input').forEach((input) => {
            input.defaultChecked = input.checked
            input.defaultValue = input.value
            input.dispatchEvent(new Event('input'))
        })
        this.checkValid()
    }

    public async submit() {
        if (!this.checkValid()) return

        let formdata = new FormData(this.form)
        let res: Response
        try {
            res = await fetch(this.endpoint, {
                method: 'POST',
                mode: 'same-origin',
                body: formdata,
                headers: {
                    'X-CSRFToken': this.csrf,
                },
            })
        } catch (e) {
            let notif = renderer.render('async-form-update-error', { error: 'Cannot connect to server' })
            displayNotification(notif, { autohide: false, delay: 20 })
            return
        }

        if (res.status === 204) {
            this.updateDefaults()
            let notif = renderer.render('async-form-update-successful', {})
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
    }
}
