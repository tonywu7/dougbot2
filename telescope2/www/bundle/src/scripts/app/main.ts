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

import { DiscordClient } from './discord'
import * as util from '../common/util'

var discord: DiscordClient

function homepage(): string {
    return (document.querySelector('#site-name a') as HTMLAnchorElement).href
}

function setSocketStatus(connected: boolean) {
    let indicator = document.querySelector('#socket-status') as HTMLSpanElement
    if (indicator === null) return
    indicator.innerHTML = `<i class="bi bi-circle-fill"></i>${connected ? 'connected' : 'disconnected'}`
    if (connected) {
        indicator.classList.add('socket-on')
        indicator.classList.remove('socket-off')
    } else {
        indicator.classList.add('socket-off')
        indicator.classList.remove('socket-on')
    }
}

function initWebSocket(): Promise<boolean> {
    return new Promise((resolve, reject) => {
        let socket = new WebSocket(`ws://${window.location.host}/bot/ws/index/`)
        socket.addEventListener('open', () => {
            setSocketStatus(true)
            return resolve(true)
        })
        socket.addEventListener('message', (ev) => {})
        socket.addEventListener('close', () => {
            setSocketStatus(false)
            setTimeout(initWebSocket, 1000)
        })
    })
}

async function discordOAuth2() {
    let authInfoContainer = document.querySelector('#discord-oauth2') as HTMLElement
    if (authInfoContainer === null) return
    let authInfo = authInfoContainer.querySelector('form') as HTMLFormElement
    let loginForm: FormData
    try {
        loginForm = new FormData(authInfo)
    } catch (e) {
        window.location.href = homepage()
        return
    }
    let accessToken = loginForm.get('access_token')?.toString()!
    if (accessToken === null) return

    discord = new DiscordClient(accessToken)
    let userCreateInfo = util.serializeFormData(loginForm)
    userCreateInfo.username = await discord.userTag()
    userCreateInfo.discord_id = await discord.userId()

    let csrfToken = loginForm.get('csrfmiddlewaretoken')?.toString()!
    let res = await fetch(window.location.pathname, {
        method: 'POST',
        mode: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken, 'Content-Type': 'application/json' },
        body: JSON.stringify(userCreateInfo),
    })
    if (res.status === 403) {
        window.location.href = authInfo.dataset.onForbidden!
    } else {
        window.location.href = homepage()
    }
}

async function setAvatar(discord: DiscordClient): Promise<void> {
    let avatarURL = (await discord.user())?.iconURL
    if (avatarURL === null || avatarURL === undefined) return
    document.querySelectorAll('.user-profile').forEach((elem) => {
        let figure = elem as HTMLElement
        figure.appendChild(createAvatarElement(avatarURL!))
    })
}

async function setGuilds(discord: DiscordClient): Promise<void> {
    let managedGuilds = await discord.managedGuilds()
}

async function initDiscord() {
    let userInfoElem = document.querySelector('#user-info') as HTMLElement
    if (userInfoElem === null) return

    let accessToken = userInfoElem.dataset.accessToken
    if (accessToken === undefined || accessToken === 'None') window.location.href = '/web/logout'

    discord = new DiscordClient(accessToken!)

    await discord.fetchUser()
    await setAvatar(discord)
}

function discordJoinServer() {
    let form = document.querySelector('#discord-join-server') as HTMLFormElement
    if (form === null) return
    form.submit()
}

export function createAvatarElement(src: string): HTMLElement {
    let img = document.createElement('img')
    img.classList.add('rounded-circle')
    img.src = src
    img.alt = `profile picture`
    return img
}

export function init() {
    discordOAuth2()
        .then(() => {
            return initDiscord()
        })
        .then(() => {
            discordJoinServer()
        })
}
