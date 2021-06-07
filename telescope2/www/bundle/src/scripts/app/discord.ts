// discord.ts
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

const API_ENDPOINT = 'https://discord.com/api/v9'

export class DiscordUser {
    readonly id: string
    readonly username: string
    readonly discriminator: string
    readonly avatar: string | null

    constructor(data: Record<string, any>) {
        this.id = data.id
        this.username = data.username
        this.discriminator = data.discriminator
        this.avatar = data.avatar
    }

    get tag(): string {
        return `${this.username}#${this.discriminator}`
    }

    get avatarURL(): string | null {
        if (this.avatar === null) return null
        return `https://cdn.discordapp.com/avatars/${this.id}/${this.avatar}.png`
    }
}

export class DiscordClient {
    _token: string

    user: DiscordUser | null = null

    constructor(accessToken: string) {
        this._token = accessToken
    }

    url(endpoint: string): string {
        return `${API_ENDPOINT}${endpoint}`
    }

    async get(endpoint: string): Promise<Record<string, any> | null> {
        let res: Response
        try {
            res = await fetch(this.url(endpoint), {
                method: 'GET',
                mode: 'cors',
                referrerPolicy: 'strict-origin-when-cross-origin',
                headers: { Authorization: `Bearer ${this._token}` },
            })
        } catch (e) {
            console.error(e)
            return null
        }
        let data: Record<string, any> = await res.json()
        if ('errors' in data) {
            console.error(`API error accessing Discord resource ${endpoint}`, data)
            return null
        }
        return data
    }

    async fetchUser() {
        let data = await this.get('/users/@me')
        if (data === null) {
            throw new Error('Error fetching current user id')
        }
        this.user = new DiscordUser(data)
    }

    async userId(): Promise<string> {
        if (this.user) return this.user.id
        await this.fetchUser()
        return this.user!.id
    }

    async userTag(): Promise<string> {
        if (this.user) return this.user.id
        await this.fetchUser()
        return this.user!.tag
    }

    async setAvatar(): Promise<void> {
        let avatarURL = this.user?.avatarURL
        if (avatarURL === null || avatarURL === undefined) return
        document.querySelectorAll('.profile-picture').forEach((elem) => {
            let figure = elem as HTMLElement
            let img = document.createElement('img')
            img.classList.add('rounded-circle')
            img.src = avatarURL!
            figure.appendChild(img)
        })
    }
}
