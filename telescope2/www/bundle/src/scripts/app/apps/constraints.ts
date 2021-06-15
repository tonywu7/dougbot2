// constraints.ts
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

import { getTemplate, randomIdentifier } from '../../common/util'
import {
    D3ItemList,
    createFlexSelect,
    initTooltips,
    createAccordion,
    Submissible,
    AsyncPostSubmit,
} from '../responsive'
import { getGuildId } from '../main'
import { ModelState } from '../constants'

interface CCRecord {
    id: number | string
    guild: string
    name: string
    type: number

    channels: string[]
    commands: string[]
    roles: string[]
}

interface CCRecordList {
    guild: string
    constraints: CCRecord[]
}

export class CommandConstraintForm {
    private container: HTMLElement
    private form: HTMLFormElement

    private title: HTMLInputElement

    private channels: D3ItemList
    private commands: D3ItemList
    private roles: D3ItemList

    private type: HTMLSelectElement

    private id: number | string
    private guildId: string

    private deleted: boolean = false
    private deleteButton: HTMLButtonElement

    constructor(data: CCRecord) {
        this.container = getTemplate('template-cmd-constraint', 'div') as HTMLElement
        this.form = this.container.querySelector('form')!

        this.id = data.id
        this.guildId = data.guild

        this.title = this.form.querySelector('.constraint-title input') as HTMLInputElement
        this.title.value = data.name
        this.title.id = `ccform-${this.id}-title`

        this.type = this.form.querySelector('.command-constraint-type') as HTMLSelectElement
        this.type.id = `ccform-${this.id}-types`
        this.type.value = data.type.toString()
        createFlexSelect(this.type.parentElement as HTMLElement)

        this.channels = new D3ItemList(this.form.querySelector('.channel-list') as HTMLElement)
        this.commands = new D3ItemList(this.form.querySelector('.command-list') as HTMLElement)
        this.roles = new D3ItemList(this.form.querySelector('.role-list') as HTMLElement)

        this.channels.setInputId(`ccform-${this.id}-channels`)
        this.commands.setInputId(`ccform-${this.id}-commands`)
        this.roles.setInputId(`ccform-${this.id}-roles`)

        this.deleteButton = this.container.querySelector('.btn-delete') as HTMLButtonElement
        this.deleteButton.addEventListener('click', this.deleteListener.bind(this))

        initTooltips(this.container)

        let fields = this.form.querySelector('.form-fields') as HTMLElement
        fields.id = `ccform-${this.id}--formfields`

        Promise.all([this.channels.populated(), this.commands.populated(), this.roles.populated()]).then(() => {
            this.channels.fromJSON(data.channels)
            this.commands.fromJSON(data.commands)
            this.roles.fromJSON(data.roles)
        })
    }

    public getElement() {
        return this.container
    }

    public static createNewForm(): CommandConstraintForm {
        let id = randomIdentifier(6)
        return new CommandConstraintForm({
            id: id,
            guild: getGuildId()!,
            name: '',
            type: 1,
            channels: [],
            commands: [],
            roles: [],
        })
    }

    deleteListener() {
        this.setDeleted(!this.deleted)
    }

    protected setDeleted(deleted: boolean) {
        this.deleted = deleted
        if (this.deleted) {
            this.deleteButton.textContent = 'Restore'
            this.title.classList.add('deleted')
        } else {
            this.deleteButton.textContent = 'Delete'
            this.title.classList.remove('deleted')
        }
    }

    private get isCreated() {
        return typeof this.id === 'string'
    }

    public toJSON(): [Partial<CCRecord>, ModelState] | [null, null] {
        let record: Partial<CCRecord> = {
            guild: this.guildId,
            name: this.title.value,
            type: Number(this.type.value),
            channels: this.channels.toJSON(),
            commands: this.commands.toJSON(),
            roles: this.roles.toJSON(),
        }
        let state: ModelState
        if (this.isCreated) {
            state = ModelState.CREATE
        } else {
            record.id = this.id
            state = ModelState.UPDATE
        }
        if (this.deleted) {
            if (state === ModelState.CREATE) {
                return [null, null]
            } else {
                state = ModelState.DELETE
            }
        }
        return [record, state]
    }

    public updateDefaults() {
        this.title.defaultValue = this.title.value
        this.setDeleted(false)
    }

    public remove() {
        this.container.parentElement?.removeChild(this.container)
    }

    public get isDeleted() {
        return this.deleted
    }
}

class CommandConstraintList {
    guild: string | null = null

    container: HTMLElement
    forms: CommandConstraintForm[] = []

    endpoint: string

    constructor(container: HTMLElement) {
        this.container = container
        this.endpoint = container.dataset.src!
        document.querySelector('#constraint-form-new')?.addEventListener('click', this.createNewForm.bind(this))
        document.querySelector('#constraint-form-submit')?.addEventListener('click', this.commit.bind(this))
        this.fetchList()
    }

    protected async fetchList() {
        let res = await fetch(this.endpoint)

        if (res.status === 404) return await this.createList()

        let data: CCRecordList = await res.json()
        this.guild = data.guild
        for (let d of data.constraints) {
            let form = new CommandConstraintForm(d)
            this.forms.push(form)
        }
        this.container.append(...this.forms.map((f) => f.getElement()))
        this.container
            .querySelectorAll('.accordion-item')
            .forEach((e) => createAccordion(this.container, e as HTMLElement))
    }

    protected async createList() {
        await fetch(this.endpoint, {
            method: 'POST',
            body: JSON.stringify({ guild: getGuildId(), constraints: [] }),
            headers: {
                'X-CSRFToken': this.getCSRF(),
                'Content-Type': 'application/json',
            },
        })
    }

    private getCSRF(): string {
        let csrf = this.container.querySelector('input[type="hidden"][name="csrfmiddlewaretoken"]') as HTMLInputElement
        return csrf.value
    }

    public createNewForm() {
        let form = CommandConstraintForm.createNewForm()
        this.forms.push(form)
        let elem = form.getElement()
        this.container.prepend(elem)
        createAccordion(this.container, elem, true)
    }

    public toJSON(): Record<ModelState, Partial<CCRecord>[]> {
        let aggregated: Record<ModelState, Partial<CCRecord>[]> = {
            [ModelState.CREATE]: [],
            [ModelState.UPDATE]: [],
            [ModelState.DELETE]: [],
        }
        for (let [data, state] of this.forms.map((f) => f.toJSON())) {
            if (data === null) continue
            data.guild = this.guild!
            if (state === ModelState.CREATE) data.id = undefined
            aggregated[state!].push(data)
        }
        return aggregated
    }

    protected putEndpoint(): string {
        return `/web/api/v1/guild/${this.guild!}/core/constraints`
    }

    protected deleteEndpoint(data: Partial<CCRecord>): string {
        return `/web/api/v1/guild/${this.guild!}/core/constraints/${data.id!}`
    }

    protected async delete(data: Partial<CCRecord>) {
        return await fetch(this.deleteEndpoint(data), {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': this.getCSRF(),
            },
        })
    }

    protected async put(data: { guild: string; constraints: Partial<CCRecord>[] }) {
        return await this.submit(JSON.stringify(data))
    }

    public getData(): Submissible {
        let data = this.toJSON()
        let submission = {
            guild: this.guild!,
            constraints: [...data[ModelState.UPDATE], ...data[ModelState.CREATE]],
        }
        return JSON.stringify(submission)
    }

    public checkValid(): boolean {
        return true
    }

    public updateDefaults() {
        for (let form of this.forms) {
            if (form.isDeleted) form.remove()
            else form.updateDefaults()
        }
    }

    public async commit() {
        let data = this.toJSON()

        let submission = {
            guild: this.guild!,
            constraints: [...data[ModelState.UPDATE], ...data[ModelState.CREATE]],
        }
        return await Promise.all([...data[ModelState.DELETE].map((d) => this.delete(d)), this.put(submission)])
    }

    public async submit(data: string, method = 'PUT') {
        return await fetch(this.putEndpoint(), {
            method: method,
            body: data,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRF(),
            },
        })
    }
}

const CommandConstraintListResponsive = AsyncPostSubmit(CommandConstraintList)

export function init() {
    let container = document.querySelector('#constraint-form-list') as HTMLElement
    if (container === null) return
    new CommandConstraintListResponsive(container)
}
