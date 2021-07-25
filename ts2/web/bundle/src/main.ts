// main.ts
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

import { Color } from './components/modal/bootstrap'
import { displayNotification } from './components/utils/modal'
import { initTooltips } from './utils/responsive'

export function homepage(): string {
    return document.querySelector<HTMLAnchorElement>('#site-name a')!.href
}

function initTopMenu() {
    let listener = (e: Event) => {
        e.stopPropagation()
        e.preventDefault()
        document
            .querySelector('.main-sidebar')!
            .classList.toggle('sidebar-visible')
    }
    let menu = document.querySelector('#top-menu-toggle')!
    menu.addEventListener('click', listener)
}

function initWidgets() {
    initTooltips(document.documentElement)
}

export function createAvatarElement(src: string): HTMLElement {
    let img = document.createElement('img')
    img.classList.add('rounded-circle')
    img.src = src
    img.alt = `profile picture`
    return img
}

function discordJoinServer() {
    let form = document.querySelector(
        '#discord-join-server form'
    ) as HTMLFormElement
    if (!form) return
    form.submit()
}

function displayServerMessages() {
    document
        .querySelectorAll<HTMLElement>('#server-messages li')
        .forEach((elem) => {
            let msg = elem.innerHTML
            let colors: Record<string, Color> = {
                debug: Color.DEBUG,
                info: Color.INFO,
                success: Color.SUCCESS,
                warning: Color.WARNING,
                error: Color.DANGER,
                critical: Color.DANGER,
            }
            displayNotification(colors[elem.className] || Color.LIGHT, msg)
        })
}

export function init() {
    initTopMenu()
    initWidgets()
    displayServerMessages()
    discordJoinServer()
}
