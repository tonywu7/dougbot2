// ItemSelect.vue.ts
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

import { color } from 'd3'

import { defineComponent, PropType, ref } from 'vue'
import InputField from './InputField.vue'

import {
    TextSearch,
    Indexable,
    configureAsPrefixSearch,
} from '../../utils/search'
import { pick } from 'lodash'

export interface ItemCandidate extends Indexable {
    id: string
    content: string
    foreground: string
    background?: string
}

export interface ItemStyle {
    color: string
    backgroundColor?: string
}

function createIndex(items: ItemCandidate[]): TextSearch<ItemCandidate> {
    return new TextSearch(items, configureAsPrefixSearch)
}

export default defineComponent({
    components: { InputField },
    props: {
        items: {
            type: Object as PropType<Record<string, ItemCandidate>>,
            required: true,
            default: () => {
                return {}
            },
        },
        label: {
            type: String,
        },
        placeholder: {
            type: String,
            default: '...',
        },
        multiple: {
            type: Boolean,
            default: true,
        },
        error: {
            type: String,
            default: '',
        },
    },
    setup() {
        const container = ref<HTMLElement>()
        const searchElem = ref<HTMLElement>()
        const searchInput = ref<HTMLTextAreaElement>()
        const candidateList = ref<HTMLUListElement>()
        return { container, searchElem, searchInput, candidateList }
    },
    // emits: ['update:choices', 'update:error'],
    data() {
        let selected: Record<string, ItemCandidate> = {}
        let index = createIndex(Object.values(this.items))
        let search: string = ''
        let ctx = document.createElement('canvas').getContext('2d')!
        return {
            selected,
            search,
            index,
            ctx,
            _currentFocus: 0,
            dropdownShow: false,
        }
    },
    computed: {
        currentFocus: {
            get(): number {
                return this._currentFocus
            },
            set(v: number) {
                this._currentFocus = v
                if (v == 0) this.scrollReset()
            },
        },
        candidates(): ItemCandidate[] {
            let items: ItemCandidate[] = []
            for (let candidate of this.index.search(this.search)) {
                items.push(candidate)
            }
            return items
        },
        inputFont(): string {
            let elem = this.searchInput
            if (elem) {
                return getComputedStyle(this.searchInput!).font
            } else {
                return '1rem sans-serif'
            }
        },
        inputWidth(): { width: string } {
            this.ctx.font = this.inputFont
            let size = this.ctx.measureText(this.search)
            let width =
                Math.abs(size.actualBoundingBoxLeft) +
                Math.abs(size.actualBoundingBoxRight)
            return { width: `calc(${width}px + 1rem)` }
        },
    },
    methods: {
        activate(ev?: FocusEvent) {
            if (this.dropdownShow) return
            this.dropdownShow = true
            this.currentFocus = 0
            this.searchInput?.focus()
        },
        deactivate(ev?: FocusEvent, force = false) {
            this.$nextTick(() => {
                if (force || !this.hasFocusWithin()) {
                    this.searchInput?.blur()
                    this.dropdownShow = false
                    this.scrollReset()
                } else {
                    this.searchInput?.focus()
                }
            })
        },
        hasFocusWithin(): boolean {
            return Boolean(
                this.container?.querySelector(':focus, :hover, :active')
            )
        },
        updateSearch() {
            this.searchInput?.setCustomValidity('')
            this.$emit('update:error', '')
            this.search = this.searchInput?.value || ''
        },
        focusSibling(inc: number): boolean {
            this.currentFocus += inc
            if (this.currentFocus < 0) {
                this.currentFocus = 0
            } else if (this.currentFocus >= this.candidates.length) {
                this.currentFocus = this.candidates.length - 1
            } else {
                return true
            }
            return false
        },
        getFocusedItem(): HTMLElement | undefined {
            return (
                this.candidateList?.querySelector<HTMLLIElement>(
                    '.has-focus'
                ) || undefined
            )
        },
        navigateList(ev: KeyboardEvent) {
            if (ev.key == 'ArrowDown' || ev.key == 'ArrowUp') {
                ev.preventDefault()
                let direction: 1 | -1 = ev.key == 'ArrowDown' ? 1 : -1
                this.focusSibling(direction)
                this.scrollByOneItem(direction)
            } else if (ev.key == 'Enter') {
                ev.preventDefault()
                this.select(this.candidates[this.currentFocus])
            } else if (ev.key == 'Escape') {
                this.deactivate(undefined, true)
            } else if (ev.key == 'Backspace') {
                if (!this.search) {
                    let item = Object.values(this.selected).pop()
                    if (!item) return
                    this.deselect(item)
                    this.search = item.content
                    ev.preventDefault()
                }
            }
        },
        scrollReset() {
            this.candidateList?.scrollTo(0, 0)
        },
        scrollByOneItem(direction: 1 | -1) {
            this.$nextTick(() => {
                let item = this.getFocusedItem()
                if (!item) return
                let container = item.parentElement!
                if (
                    (direction == 1 &&
                        container.scrollTop + container.clientHeight <
                            item.offsetTop + item.clientHeight) ||
                    (direction == -1 && container.scrollTop > item.offsetTop)
                )
                    this.candidateList?.scrollBy(
                        0,
                        item.clientHeight * direction
                    )
            })
        },
        getItemStyles(item: ItemCandidate, background = true): ItemStyle {
            let fg = color(item.foreground)
            let styles: ItemStyle = {
                color: fg?.formatRgb() || '#d3d3d3',
            }
            if (background) {
                let bg = item.background
                    ? color(item.background)
                    : fg?.copy({ opacity: 0.15 })
                styles.backgroundColor =
                    bg?.formatRgb() || 'rgba(211, 211, 211, .15)'
            }
            return styles
        },
        select(item: ItemCandidate) {
            if (!this.multiple) {
                Object.keys(this.selected).forEach(
                    (k) => delete this.selected[k]
                )
            }
            this.selected[item.id] = item
            this.search = ''
            this.update()
        },
        deselect(item: ItemCandidate) {
            delete this.selected[item.id]
            this.update()
        },
        update() {
            this.$emit('update:choices', Object.keys(this.selected))
        },
        regenIndex() {
            this.index = createIndex(Object.values(this.items))
        },
    },
    watch: {
        candidates() {
            this.currentFocus = 0
        },
        error(e: string) {
            this.searchInput!.setCustomValidity(e)
            this.searchInput!.reportValidity()
        },
        items: {
            handler() {
                this.regenIndex()
            },
            deep: true,
        },
        '$attrs.choices': {
            handler(keys: string[]) {
                let selected: Record<string, ItemCandidate> = {}
                for (let k of keys) {
                    let item = this.items[k]
                    if (item) {
                        selected[k] = item
                    } else {
                        selected[k] = {
                            id: k,
                            content: k,
                            foreground: 'white',
                            getIndex: () => ({ id: k }),
                        }
                    }
                }
                this.selected = selected
            },
            deep: true,
            immediate: true,
        },
    },
})
