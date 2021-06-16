// core.ts
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

import { D3ItemList } from '../responsive'

function widgetPrefixLiveUpdate() {
    let prefix: string = ''
    let input = document.querySelector('input#id_prefix') as HTMLInputElement
    if (!input) return
    let updatePrefixes = () => {
        prefix = input.value
        document.querySelectorAll('.data-command-prefix').forEach((e) => (e.textContent = prefix))
    }
    input?.addEventListener('input', () => {
        updatePrefixes()
    })
    updatePrefixes()
}

function initLoggingView() {
    document.querySelectorAll('#logging .d3-item-list').forEach((e) => new D3ItemList(e as HTMLElement))
}

export function init() {
    widgetPrefixLiveUpdate()
    initLoggingView()
}
