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
const CDN_PREFIX = 'https://cdn.discordapp.com'

interface DiscordIdentity {
    readonly id: string
    readonly type: string
}

interface HasName {
    readonly name: string
}

interface HasIcon {
    readonly iconURL: string | null
}

export class User implements DiscordIdentity, HasIcon, HasName {
    readonly id: string
    readonly type: string = 'users'
    readonly username: string
    readonly discriminator: string
    readonly avatar: string | null

    constructor(data: Record<string, any>) {
        this.id = data.id
        this.username = data.username
        this.discriminator = data.discriminator
        this.avatar = data.avatar
    }

    get name(): string {
        return `${this.username}#${this.discriminator}`
    }

    get iconURL(): string | null {
        if (this.avatar === null) return null
        return `${CDN_PREFIX}/avatars/${this.id}/${this.avatar}.png`
    }
}

export class Guild implements DiscordIdentity, HasIcon, HasName {
    readonly id: string
    readonly type: string = 'users'

    readonly name: string
    readonly icon: string | null

    readonly permissions: Permission | null

    constructor(data: Record<string, any>) {
        this.id = data.id
        this.name = data.name
        this.icon = data.icon
        this.permissions = data.permissions && new Permission(data.permissions)
    }

    get iconURL(): string {
        return `${CDN_PREFIX}/icons/${this.id}/${this.icon}.png`
    }
}

export class Permission {
    private readonly perm: number

    constructor(permLiteral: string | number) {
        this.perm = Number(permLiteral)
    }

    hasPerms(other: Permission): boolean {
        return Boolean(this.perm & other.perm)
    }

    intersect(other: Permission): Permission {
        return new Permission(this.perm & other.perm)
    }

    union(other: Permission): Permission {
        return new Permission(this.perm | other.perm)
    }
}

export class Perms {
    static readonly ADMINISTRATOR = new Permission(1 << 3)
    static readonly MANAGE_GUILD = new Permission(1 << 5)
}

export class DiscordClient {
    _token: string

    user: User | null = null

    _guilds: Guild[] = []

    constructor(accessToken: string) {
        this._token = accessToken
    }

    url(endpoint: string): string {
        return `${API_ENDPOINT}${endpoint}`
    }

    async get(endpoint: string): Promise<Record<string, any> | Promise<Record<string, any>[]> | null> {
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
        if (res.status === 401) {
            window.location.href = '/web/logout'
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
        this.user = new User(data)
    }

    async userId(): Promise<string> {
        if (this.user) return this.user.id
        await this.fetchUser()
        return this.user!.id
    }

    async userTag(): Promise<string> {
        if (this.user) return this.user.id
        await this.fetchUser()
        return this.user!.name
    }

    async setAvatar(): Promise<void> {
        let avatarURL = this.user?.iconURL
        if (avatarURL === null || avatarURL === undefined) return
        document.querySelectorAll('.profile-picture').forEach((elem) => {
            let figure = elem as HTMLElement
            let img = document.createElement('img')
            img.classList.add('rounded-circle')
            img.src = avatarURL!
            figure.appendChild(img)
        })
    }

    async fetchGuilds(): Promise<Guild[]> {
        if (this._guilds.length) return [...this._guilds]
        let data: Record<string, any>[] = (await this.get('/users/@me/guilds')) as Record<string, any>[]
        if (data === null) return []
        this._guilds = data.map((d) => new Guild(d))
        return [...this._guilds]
    }

    async managedGuilds(): Promise<Guild[]> {
        let guilds = await this.fetchGuilds()
        return guilds.filter((g) => g.permissions?.hasPerms(Perms.MANAGE_GUILD))
    }
}
