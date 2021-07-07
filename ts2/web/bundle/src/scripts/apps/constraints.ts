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

import { getTemplate, randomIdentifier } from '../util'
import { D3ItemList, createFlexSelect, initTooltips, createAccordion } from '../responsive'
import { getGuildId } from '../main'
import { ModelState } from '../constants'
import { AsyncModelForm } from '../form'

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

export class CommandConstraintForm extends AsyncModelForm {
    private container: HTMLElement

    private title: HTMLInputElement

    private channels: D3ItemList
    private commands: D3ItemList
    private roles: D3ItemList

    private type: HTMLSelectElement

    public id: number | string
    private guildId: string

    private deleted: boolean = false
    private deleteButton: HTMLButtonElement

    constructor(container: HTMLElement, form: HTMLFormElement, data: CCRecord) {
        super(form)
        this.container = container

        this.id = data.id
        this.guildId = data.guild

        this.title = this.form?.querySelector<HTMLInputElement>('.constraint-title input')!
        this.title.value = data.name

        this.type = this.form?.querySelector<HTMLSelectElement>('.command-constraint-type')!
        this.type.value = data.type.toString()
        createFlexSelect(this.type.parentElement as HTMLElement)

        this.channels = new D3ItemList(this.form?.querySelector<HTMLElement>('.channel-list')!)
        this.commands = new D3ItemList(this.form?.querySelector<HTMLElement>('.command-list')!)
        this.roles = new D3ItemList(this.form?.querySelector<HTMLElement>('.role-list')!)

        this.deleteButton = this.container.querySelector<HTMLButtonElement>('.btn-delete')!
        this.deleteButton.addEventListener('click', this.deleteListener.bind(this))

        initTooltips(this.container)
        this.setElementIds()

        this.channels.input.addEventListener('change', this.setSpecificity.bind(this))
        this.commands.input.addEventListener('change', this.setSpecificity.bind(this))
        this.type.addEventListener('change', this.setSpecificity.bind(this))

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
        return Number(!this.channels.isEmpty) * 2 + Number(!this.commands.isEmpty) + Number(this.type.value === '0') * 4
    }

    protected setSpecificity() {
        this.container.querySelector('.constraint-specificity')!.textContent = this.getSpecificity().toString()
    }

    public static createNewForm(data?: CCRecord): CommandConstraintForm {
        let id = randomIdentifier(6)
        let container = getTemplate('template-cmd-constraint', 'div') as HTMLElement
        let form = container.querySelector('form')!
        data = data || {
            id: id,
            guild: getGuildId()!,
            name: '',
            type: 1,
            channels: [],
            commands: [],
            roles: [],
        }
        return new CommandConstraintForm(container, form, data)
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

    public checkValidity(): boolean {
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
        let fields = this.form!.querySelector<HTMLElement>('.form-fields')!
        fields.id = `ccform-${this.id}--formfields`
        this.container.querySelector<HTMLLabelElement>('.channels label')!.htmlFor = `ccform-${this.id}-channels`
        this.container.querySelector<HTMLLabelElement>('.commands label')!.htmlFor = `ccform-${this.id}-commands`
        this.container.querySelector<HTMLLabelElement>('.roles label')!.htmlFor = `ccform-${this.id}-roles`
    }
}

class CommandConstraintList extends AsyncModelForm {
    guild: string | null

    container: HTMLElement
    forms: Record<string, CommandConstraintForm> = {}

    constructor(container: HTMLElement) {
        super(undefined)
        this.guild = getGuildId()
        this.container = container
        this.endpoint = container.dataset.src!
        document.querySelector('#constraint-form-new')?.addEventListener('click', this.createNewForm.bind(this))
        document.querySelector('#constraint-form-submit')?.addEventListener('click', this.submit.bind(this))
        this.fetchList()
    }

    protected async fetchList() {
        if (!this.endpoint) return
        let res = await fetch(this.endpoint)
        if (res.status === 404) return await this.createList()
        let data: CCRecordList = await res.json()
        this.parseData(data)
    }

    protected parseData(data: CCRecordList) {
        this.clear()
        for (let d of data.constraints) {
            let form = CommandConstraintForm.createNewForm(d)
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
        if (!this.endpoint) return
        await fetch(this.endpoint, {
            method: 'POST',
            body: JSON.stringify({ guild: getGuildId(), constraints: [] }),
            headers: {
                'X-CSRFToken': this.getCSRF(),
                'Content-Type': 'application/json',
            },
        })
    }

    protected getCSRF(): string {
        let csrf = this.container.querySelector<HTMLInputElement>('input[type="hidden"][name="csrfmiddlewaretoken"]')!
        return csrf.value
    }

    public createNewForm() {
        let form = CommandConstraintForm.createNewForm()
        this.forms[form.id] = form
        let elem = form.getElement()
        this.container.prepend(elem)
        createAccordion(this.container, elem, true)
    }

    public toMutations(): Record<ModelState, Partial<CCRecord>[]> {
        let aggregated: Record<ModelState, Partial<CCRecord>[]> = {
            [ModelState.CREATE]: [],
            [ModelState.UPDATE]: [],
            [ModelState.DELETE]: [],
        }
        for (let [data, state] of Object.values(this.forms).map((f) => f.toJSON())) {
            if (!data) continue
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

    public getJSON(data: Record<ModelState, Partial<CCRecord>[]>) {
        let submission = {
            guild: this.guild!,
            constraints: [...data[ModelState.UPDATE], ...data[ModelState.CREATE]],
        }
        return submission
    }

    public toList() {
        return this.getJSON(this.toMutations())
    }

    public checkValidity(): boolean {
        for (let form of Object.values(this.forms)) {
            if (!form.checkValidity()) return false
        }
        return true
    }

    public updateDefaults() {
        for (let form of Object.values(this.forms)) {
            if (form.isDeleted) form.remove()
            else form.updateDefaults()
        }
    }

    protected async post() {
        return null
    }

    protected async delete(data: Partial<CCRecord>): Promise<Response> {
        return await fetch(this.deleteEndpoint(data), {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': this.getCSRF(),
            },
        })
    }

    protected async put(data: { guild: string; constraints: Partial<CCRecord>[] }): Promise<Response> {
        let response = await fetch(this.putEndpoint(), {
            method: 'PUT',
            body: JSON.stringify(data),
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCSRF(),
            },
        })
        if (response.status < 299) {
            let res = response.clone()
            let results: CCRecordList = await res.json()
            this.parseData(results)
        }
        return response
    }

    public async submit() {
        if (!this.checkValidity()) return null
        let data = this.toMutations()
        let submission = this.getJSON(data)
        let responses = await Promise.all([...data[ModelState.DELETE].map((d) => this.delete(d)), this.put(submission)])
        return await this.postSubmit(responses[responses.length - 1])
    }
}

class CommandConstraintPreviewer {
    list: CommandConstraintList
    container: HTMLElement
    form: HTMLFormElement
    endpoint: string

    private channel: D3ItemList
    private command: D3ItemList
    private roles: D3ItemList

    result: HTMLElement

    constructor(container: HTMLElement, list: CommandConstraintList) {
        this.list = list
        this.container = container
        this.form = container.querySelector('form')!
        this.endpoint = this.form.action

        this.channel = new D3ItemList(this.container.querySelector<HTMLElement>('.channel-list')!)
        this.command = new D3ItemList(this.container.querySelector<HTMLElement>('.command-list')!)
        this.roles = new D3ItemList(this.container.querySelector<HTMLElement>('.role-list')!)
        this.result = this.container.querySelector<HTMLElement>('.test-result')!

        this.container.querySelector('.btn-submit')?.addEventListener('click', this.run.bind(this))

        this.channel.input.addEventListener('change', () => this.setResult(undefined))
        this.command.input.addEventListener('change', () => this.setResult(undefined))
        this.roles.input.addEventListener('change', () => this.setResult(undefined))

        Promise.all([this.channel.populated(), this.command.populated(), this.roles.populated()])
    }

    async run() {
        for (let list of [this.roles, this.command, this.channel]) {
            if (list.isEmpty) {
                list.setValidity('This field cannot be empty')
                return
            }
        }
        let data = {
            config: this.list.toList(),
            channel: this.channel.toJSON(),
            command: this.command.toJSON(),
            roles: this.roles.toJSON(),
        }
        let res = await fetch(this.endpoint, {
            method: 'POST',
            body: JSON.stringify(data),
            headers: { 'Content-Type': 'application/json' },
        })
        let result = await res.json()
        this.setResult(result.result)
    }

    setResult(result: boolean | undefined) {
        if (result === undefined) {
            this.result.innerHTML = '...'
            return
        }
        let value: HTMLElement = document.createElement('span')
        let command: HTMLElement = this.command.copyElements()
        let channel: HTMLElement = this.channel.copyElements()
        if (result === true) {
            value.innerHTML = '<i class="bi bi-circle-fill"></i> allowed'
            value.classList.add('text-on')
        } else if (result === false) {
            value.innerHTML = '<i class="bi bi-circle-fill"></i> not allowed'
            value.classList.add('text-off')
        }
        this.result.innerHTML = `This member is ${value.outerHTML} to use ${command.outerHTML} in ${channel.outerHTML}`
    }
}

export function init() {
    let formlist = document.querySelector<HTMLElement>('#constraint-form-list')
    if (!formlist) return
    let list = new CommandConstraintList(formlist)
    let preview = document.querySelector<HTMLElement>('#constraint-inspector')!
    new CommandConstraintPreviewer(preview, list)
}
