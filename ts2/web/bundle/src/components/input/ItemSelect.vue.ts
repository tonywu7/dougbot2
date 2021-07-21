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
import { Dropdown } from 'bootstrap'

import { defineComponent, PropType } from 'vue'
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
    emits: ['update:choices', 'update:error'],
    mounted() {
        let elem = this.$refs.dropdown as HTMLElement
        elem.addEventListener('hidden.bs.dropdown', () => {
            this.search = ''
        })
    },
    data() {
        let selected: Record<string, ItemCandidate> = {}
        let index = createIndex(Object.values(this.items))
        let search: string = ''
        return {
            selected,
            search,
            index,
        }
    },
    computed: {
        dropdown(): Dropdown {
            let elem = this.$refs.dropdown as HTMLElement
            let dropdown = Dropdown.getInstance(elem)
            if (!dropdown) {
                dropdown = new Dropdown(elem)
            }
            return dropdown
        },
        candidates(): ItemCandidate[] {
            let items: ItemCandidate[] = []
            for (let candidate of this.index.search(this.search)) {
                items.push(candidate)
            }
            return items
        },
    },
    methods: {
        showDropdown(ev?: MouseEvent | FocusEvent) {
            ev?.stopImmediatePropagation()
            this.dropdown?.show()
        },
        clearValidity() {
            let searchBox = this.$refs.searchBox as HTMLInputElement
            searchBox.setCustomValidity('')
            this.$emit('update:error', '')
        },
        hideDropdown(ev: FocusEvent) {
            let focused = ev.relatedTarget as HTMLElement
            if (focused && !focused.classList.contains('item-select-item')) {
                this.dropdown?.hide()
            }
        },
        styles(item: ItemCandidate, background = true): ItemStyle {
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
        select(ev: MouseEvent, item: ItemCandidate) {
            if (!this.multiple) {
                this.dropdown?.hide()
            }
            if (!this.multiple) {
                Object.keys(this.selected).forEach(
                    (k) => delete this.selected[k]
                )
            }
            this.selected[item.id] = item
            this.update()
        },
        deselect(ev: MouseEvent, item: ItemCandidate) {
            ev.stopImmediatePropagation()
            delete this.selected[item.id]
            this.update()
        },
        update() {
            this.$emit(
                'update:choices',
                pick(this.items, Object.keys(this.selected))
            )
        },
        regenIndex() {
            this.index = createIndex(Object.values(this.items))
        },
    },
    watch: {
        error(e: string) {
            let searchBox = this.$refs.searchBox as HTMLInputElement
            searchBox.setCustomValidity(e)
            searchBox.reportValidity()
        },
        items: {
            handler() {
                this.regenIndex()
            },
            deep: true,
        },
        '$attrs.choices': {
            handler(v: Record<string, ItemCandidate>) {
                this.selected = v
            },
            deep: true,
            immediate: true,
        },
    },
})

export function candidateWithDefault(
    keys: string[],
    items: Record<string, ItemCandidate>,
    ifndef: (id: string) => string
) {
    let selected: Record<string, ItemCandidate> = {}
    for (let k of keys) {
        selected[k] = items[k] || {
            id: k,
            content: ifndef(k),
            foreground: 'white',
            getIndex: () => ({ id: k }),
        }
    }
    return selected
}
