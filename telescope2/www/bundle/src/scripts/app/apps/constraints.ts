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
    tempId?: any
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

    public id: number | string
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

        this.type = this.form.querySelector('.command-constraint-type') as HTMLSelectElement
        this.type.value = data.type.toString()
        createFlexSelect(this.type.parentElement as HTMLElement)

        this.channels = new D3ItemList(this.form.querySelector('.channel-list') as HTMLElement)
        this.commands = new D3ItemList(this.form.querySelector('.command-list') as HTMLElement)
        this.roles = new D3ItemList(this.form.querySelector('.role-list') as HTMLElement)

        this.deleteButton = this.container.querySelector('.btn-delete') as HTMLButtonElement
        this.deleteButton.addEventListener('click', this.deleteListener.bind(this))

        initTooltips(this.container)
        this.setElementIds()

        this.channels.input.addEventListener('change', this.setSpecificity.bind(this))
        this.commands.input.addEventListener('change', this.setSpecificity.bind(this))

        Promise.all([this.channels.populated(), this.commands.populated(), this.roles.populated()]).then(() => {
            this.channels.fromJSON(data.channels)
            this.commands.fromJSON(data.commands)
            this.roles.fromJSON(data.roles)
            this.setSpecificity()
        })
    }

    public getElement() {
        return this.container
    }

    public getSpecificity(): number {
        return Number(!this.channels.isEmpty) * 2 + Number(!this.commands.isEmpty)
    }

    protected setSpecificity() {
        this.container.querySelector('.constraint-specificity')!.textContent = this.getSpecificity().toString()
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

    protected getName(): string {
        let name = this.title.value
        if (name.length) {
            return name
        } else {
            return '(unnamed constraint)'
        }
    }

    public checkValid(): boolean {
        this.title.setCustomValidity('')
        if (this.deleted) return true
        if (!this.title.checkValidity()) {
            return this.title.reportValidity()
        }
        if (this.roles.isEmpty) {
            this.title.setCustomValidity('Roles cannot be empty')
            this.title.reportValidity()
            return false
        }
        return true
    }

    public updateDefaults() {
        this.title.defaultValue = this.title.value
        this.setDeleted(false)
    }

    public remove() {
        this.container.parentElement?.removeChild(this.container)
    }

    public get isCreated() {
        return typeof this.id === 'string'
    }

    public get isDeleted() {
        return this.deleted
    }

    public setId(id: number) {
        this.id = id
        this.setElementIds()
    }

    protected setElementIds() {
        this.title.id = `ccform-${this.id}-title`
        this.type.id = `ccform-${this.id}-types`
        this.channels.setInputId(`ccform-${this.id}-channels`)
        this.commands.setInputId(`ccform-${this.id}-commands`)
        this.roles.setInputId(`ccform-${this.id}-roles`)
        let fields = this.form.querySelector('.form-fields') as HTMLElement
        fields.id = `ccform-${this.id}--formfields`
    }
}

class CommandConstraintList {
    guild: string | null

    container: HTMLElement
    forms: Record<string, CommandConstraintForm> = {}

    endpoint: string

    constructor(container: HTMLElement) {
        this.guild = getGuildId()
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
        this.parseData(data)
    }

    protected parseData(data: CCRecordList) {
        this.clear()
        for (let d of data.constraints) {
            let form = new CommandConstraintForm(d)
            this.forms[form.id] = form
        }
        this.container.append(...Object.values(this.forms).map((f) => f.getElement()))
        this.container
            .querySelectorAll('.accordion-item')
            .forEach((e) => createAccordion(this.container, e as HTMLElement))
    }

    protected clear() {
        for (let [k, v] of Object.entries(this.forms)) {
            v.remove()
        }
        this.forms = {}
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
        this.forms[form.id] = form
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
        for (let [data, state] of Object.values(this.forms).map((f) => f.toJSON())) {
            if (data === null) continue
            data.guild = this.guild!
            if (state === ModelState.CREATE) {
                data.tempId = data.id
                data.id = undefined
            }
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
        let response = await this.submit(JSON.stringify(data))
        if (response.status < 299) {
            let res = response.clone()
            let results: CCRecordList = await res.json()
            this.parseData(results)
        }
        return response
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
        for (let form of Object.values(this.forms)) {
            if (!form.checkValid()) return false
        }
        return true
    }

    public updateDefaults() {
        for (let form of Object.values(this.forms)) {
            if (form.isDeleted) form.remove()
            else form.updateDefaults()
        }
    }

    public async commit() {
        if (!this.checkValid()) return

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
