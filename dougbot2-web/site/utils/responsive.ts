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

type JSONValue = string | number | boolean | null
type JSONArray = Array<JSONValue | JSONType>
interface JSONType extends Record<string, JSONValue | JSONArray | JSONType> {}

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

export function createAccordion(
    parent: HTMLElement,
    target: HTMLElement,
    toggle: boolean = false
) {
    let toggleElem = target.querySelector('.accordion-button') as HTMLElement
    let collapseElem = target.querySelector(
        '.accordion-collapse'
    ) as HTMLElement
    toggleElem.dataset.bsTarget = `#${collapseElem.id}`
    collapseElem.dataset.bsParent = `#${parent.id}`
    return new bootstrap.Collapse(collapseElem, {
        parent: parent,
        toggle: toggle,
    })
}

export function initTooltips(frame: Element) {
    ;[].slice
        .call(frame.querySelectorAll('[data-bs-toggle="tooltip"]'))
        .forEach((tooltipElem) => new bootstrap.Tooltip(tooltipElem))
}

export function sleep(s: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, s * 1000))
}
