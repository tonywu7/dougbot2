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
import * as d3 from 'd3'
import { TextSearch, configureAsPrefixSearch, allKeywords } from './search'
import { datasources, renderer } from './main'

type JSONValue = string | number | boolean | null
type JSONArray = Array<JSONValue | JSONType>
interface JSONType extends Record<string, JSONValue | JSONArray | JSONType> {}

export interface D3Datum {
    id: string
    type?: string | number
    name?: string
    color?: number
    order?: number
}

class D3Item implements D3Datum {
    static DEFAULT_COLOR = '#98a9ea'

    id: string
    type?: string | number
    name?: string
    color?: number
    order?: number

    constructor(data: any) {
        Object.assign(this, data)
        this.id = data.id.toString()
    }

    getIndex() {
        return {
            id: this.id,
            name: this.name || this.id,
        }
    }

    getColor(): string {
        if (!this.color) return D3Item.DEFAULT_COLOR
        let hex = (this.color as number).toString(16)
        return `#${hex}`
    }

    getBackgroundColor(): string {
        let c = d3.color(this.getColor())!
        c.opacity = 0.15
        return c.toString()
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
    dataSource: string
    selectionType: 'single' | 'multiple'

    selected: Record<any, D3Item> = {}
    selection: d3.Selection<HTMLElement, D3Item, HTMLElement, unknown> | null = null
    candidates: d3.Selection<HTMLLIElement, D3Item, HTMLUListElement, any> | null = null
    index: TextSearch<D3Item> | null = null

    private initialFetch: Promise<void>

    constructor(container: HTMLElement) {
        this.container = container

        this.input = container.querySelector('input[data-target]') as HTMLInputElement
        this.field = container.querySelector('.form-control') as HTMLElement
        this.userEntry = this.field.querySelector('input[type="text"]') as HTMLInputElement

        this.dropdownToggle = container.querySelector('[data-bs-toggle="dropdown"]') as HTMLElement
        this.dropdownMenu = container.querySelector('.dropdown') as HTMLElement
        this.dropdown = new bootstrap.Dropdown(this.dropdownToggle)

        this.itemList = this.dropdownMenu.querySelector('ul') as HTMLUListElement
        this.dataSource = this.container.dataset.src!
        this.selectionType = this.container.dataset.selectionType as any

        this.addListeners()
        this.initialFetch = this.populate()
    }

    private addListeners() {
        this.userEntry.addEventListener('click', () => this.userEntry.select())
        this.userEntry.addEventListener('keydown', this.keyboardListener.bind(this))
        this.userEntry.addEventListener('input', this.searchListener.bind(this))
        this.userEntry.addEventListener('hidden.bs.dropdown', () => {
            this.userEntry.value = ''
            this.filter('')
        })
    }

    public async populate() {
        let data = await datasources.data(this.dataSource)
        let objs: D3Item[] = data.map((d) => new D3Item(d))

        this.index = new TextSearch(objs, configureAsPrefixSearch)
        this.candidates = d3
            .select(this.itemList)
            .selectAll('li')
            .data(objs)
            .enter()
            .append('li')
            .attr('class', 'dropdown-item')
            .attr('tabindex', '0')
            .sort(
                (x, y) => Number(x.order) - Number(y.order) || d3.ascending(x.name, y.name) || d3.ascending(x.id, y.id)
            )
            .on('click', this.addItem.bind(this))
            .on('keydown', this.keyboardListener.bind(this))
        this.candidates
            .append('span')
            .attr('class', 'd3-item')
            .attr('data-item-id', (d) => d.id)
            .attr('data-item-type', (d) => d.type || 0)
            .text((d) => d.name || d.id)
            .style('color', (d) => d.getColor())

        let initialData = this.input.value
        if (!initialData.length) return
        this.fromJSON(initialData.split(','))
    }

    public async populated(): Promise<boolean> {
        await this.initialFetch
        return true
    }

    protected updateSelection() {
        let select = d3.select(this.field).selectAll('span.d3-selected') as d3.Selection<
            HTMLElement,
            D3Datum,
            HTMLElement,
            unknown
        >
        this.selection = select.data(Object.values(this.selected))
        this.selection
            .enter()
            .insert('span', 'input')
            .attr('tabindex', '0')
            .attr('class', 'token d3-item d3-selected')
            .attr('data-item-id', (d) => d.id)
            .attr('data-item-type', (d) => d.type || 0)
            .text((d) => d.name || d.id)
            .style('color', (d) => d.getColor())
            .style('background-color', (d) => d.getBackgroundColor())
            .on('click', this.removeItem.bind(this))
            .on('keydown', this.keyboardListener.bind(this))
        this.selection.exit().remove()
    }

    protected addItem(event: MouseEvent, d: D3Item) {
        d3.select(this.field).selectAll('span.d3-selected').remove()
        if (this.selectionType === 'single') {
            this.selected = { [d.id]: d }
        } else {
            this.selected[d.id] = d
        }
        this.updateSelection()
        this.updateValue()
        this.dropdown.update()
    }

    protected removeItem(event: MouseEvent, d: D3Item) {
        delete this.selected[d.id]
        d3.select(this.field).selectAll(`.d3-selected[data-item-id="${d.id}"]`).remove()
        this.updateValue()
        this.dropdown.update()
    }

    protected updateValue() {
        let ids: string[] = Object.keys(this.selected)
        this.input.value = ids.join('\x00')
        this.input.dispatchEvent(new Event('change'))
    }

    public setSelection(selection: string) {
        let ids: string[]
        if (!selection.length) {
            ids = []
        } else {
            ids = selection.split('\x00')
        }
        this.fromJSON(ids)
    }

    public searchListener() {
        if (!this.expanded) this.dropdown.show()
        this.setValidity('')
        this.filter(this.userEntry.value)
    }

    public filter(terms: string) {
        let matches = new Set(this.index!.query(allKeywords(terms)).map((r) => r.ref))
        this.candidates!.filter((d) => !matches.has(d.id)).attr('class', 'dropdown-item hidden')
        this.candidates!.filter((d) => matches.has(d.id)).attr('class', 'dropdown-item')
    }

    public get expanded(): boolean {
        return this.itemList.classList.contains('show')
    }

    protected keyboardListener(ev: KeyboardEvent): void {
        if (ev.key === 'Enter') {
            ;(ev.target as HTMLElement).click()
        }
    }

    protected blur() {
        this.userEntry.blur()
    }

    public fromJSON(items: string[]) {
        let ids = new Set(items)
        let data = this.candidates!.filter((d) => ids.has(d.id)).data()
        this.selected = Object.assign({}, ...data.map((d) => ({ [d.id]: d })))
        this.updateSelection()
        this.updateValue()
    }

    public toJSON(): string[] {
        let data = this.input.value.split('\x00')
        return data.filter((s) => s.length > 0)
    }

    public setInputId(id: string) {
        this.input.id = id
    }

    public get isEmpty(): boolean {
        return Object.keys(this.selected).length === 0
    }

    public checkValidity(): boolean {
        if (this.input.required && this.isEmpty) {
            this.setValidity('Please fill out this field')
            return false
        }
        return true
    }

    public setValidity(message: string) {
        this.userEntry.setCustomValidity(message)
        this.userEntry.reportValidity()
    }

    public copyElements(): HTMLSpanElement {
        let span = document.createElement('span')
        span.append(
            ...(d3.select(this.field).selectAll('span.d3-selected').nodes() || []).map((n) =>
                (n as Node).cloneNode(true)
            )
        )
        return span
    }
}

export function createFlexSelect(e: HTMLElement) {
    let select = e.querySelector('select') as HTMLSelectElement
    if (!select) return
    let text = e.querySelector('.actionable') as HTMLElement
    select.addEventListener('change', () => {
        let selected = select.selectedOptions
        let hint = selected ? selected[0].textContent : '(none)'
        if (text) {
            text.textContent = hint
            text.dataset.value = selected.item(0)!.value
        }
    })
    select.dispatchEvent(new Event('change'))
}

export function createAccordion(parent: HTMLElement, target: HTMLElement, toggle: boolean = false) {
    let toggleElem = target.querySelector('.accordion-button') as HTMLElement
    let collapseElem = target.querySelector('.accordion-collapse') as HTMLElement
    toggleElem.dataset.bsTarget = `#${collapseElem.id}`
    collapseElem.dataset.bsParent = `#${parent.id}`
    return new bootstrap.Collapse(collapseElem, { parent: parent, toggle: toggle })
}

export function initTooltips(frame: Element) {
    ;[].slice
        .call(frame.querySelectorAll('[data-bs-toggle="tooltip"]'))
        .forEach((tooltipElem) => new bootstrap.Tooltip(tooltipElem))
}

export interface D3DataSource {
    data(dtype: string): Promise<D3Datum[]>
}