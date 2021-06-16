// login.ts
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
import { homepage } from './main'

import * as util from '../common/util'

export var discord: DiscordClient

async function discordOAuth2() {
    let authInfoContainer = document.querySelector('#discord-oauth2') as HTMLElement
    if (!authInfoContainer) return
    let authInfo = authInfoContainer.querySelector('form') as HTMLFormElement
    let loginForm: FormData
    try {
        loginForm = new FormData(authInfo)
    } catch (e) {
        window.location.href = homepage()
        return
    }
    let accessToken = loginForm.get('access_token')?.toString()!
    if (!accessToken) return

    discord = new DiscordClient(accessToken)
    let userCreateInfo = util.serializeFormData(loginForm)
    userCreateInfo.username = await discord.userTag()
    userCreateInfo.snowflake = await discord.userId()

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

async function initDiscord() {
    let userInfoElem = document.querySelector('#user-info') as HTMLElement
    if (!userInfoElem) return

    let accessToken = userInfoElem.dataset.accessToken
    if (accessToken === undefined || accessToken === 'None') window.location.href = '/web/logout'

    discord = new DiscordClient(accessToken!)
}

function discordJoinServer() {
    let form = document.querySelector('#discord-join-server form') as HTMLFormElement
    if (!form) return
    form.submit()
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
