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

import { DiscordServer } from './discord'
import { TemplateRenderer, initTooltips, D3DataSource } from './responsive'
import { AsyncModelForm } from './form'

import { BotData } from './bot'

export var renderer: TemplateRenderer

export var datasources: DataSources

export function homepage(): string {
    return (document.querySelector('#site-name a') as HTMLAnchorElement).href
}

function initTopMenu() {
    let listener = (e: Event) => {
        e.stopPropagation()
        e.preventDefault()
        document.querySelector('.main-sidebar')!.classList.toggle('sidebar-visible')
    }
    let menu = document.querySelector('#top-menu-toggle')!
    menu.addEventListener('click', listener)
}

function initWidgets() {
    document.querySelectorAll('.async-form').forEach((form) => {
        new AsyncModelForm(form as HTMLFormElement)
    })

    initTooltips(document.documentElement)
}

function initTemplates() {
    renderer = new TemplateRenderer(document.querySelector('#template-container') as HTMLElement)
}

export function createAvatarElement(src: string): HTMLElement {
    let img = document.createElement('img')
    img.classList.add('rounded-circle')
    img.src = src
    img.alt = `profile picture`
    return img
}

export function getGuildId(): string | null {
    let elem = document.querySelector('[data-server-id]')
    if (!elem) return null
    return (elem as HTMLElement).dataset.serverId!
}

class DataSources {
    src: Record<string, D3DataSource> = {}

    constructor() {
        this.src['discord'] = new DiscordServer(getGuildId()!)
        this.src['bot'] = new BotData()
    }

    async data(uri: string) {
        let [namespace, dtype, ...args] = uri.split(':')
        return await this.src[namespace].data(dtype)
    }
}

export function init() {
    datasources = new DataSources()
    initTopMenu()
    initWidgets()
    initTemplates()
}
