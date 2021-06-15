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

import { D3DataSource, D3Datum } from './responsive'

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
    private _token: string

    private _user: User | null = null
    private _guilds: Guild[] = []
    private _currentGuild: Guild | null = null

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
        this._user = new User(data)
    }

    async user(): Promise<User> {
        if (this._user) return this._user
        await this.fetchUser()
        return this._user!
    }

    async userId(): Promise<string> {
        return (await this.user()).id
    }

    async userTag(): Promise<string> {
        return (await this.user()).name
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

export class Channel implements D3Datum {
    id: string
    type?: string | number
    name?: string
    order?: number

    constructor(data: any) {
        Object.assign(this, data)
        this.id = data.id.toString()
    }
}

export class Role implements D3Datum {
    id: string
    color?: number
    name?: string
    order?: number

    constructor(data: any) {
        Object.assign(this, data)
        this.id = data.id.toString()
    }
}

export class DiscordServer implements D3DataSource {
    readonly id: string

    private _name: string = ''

    private readonly channels: Channel[] = []
    private readonly roles: Role[] = []

    private initialFetch: Promise<void>

    constructor(id: string) {
        this.id = id
        this.initialFetch = this.fetchData()
    }

    get endpoint(): string {
        return `/web/api/v1/guild/${this.id}`
    }

    get name() {
        return this._name
    }

    async fetchData(): Promise<void> {
        let res = await fetch(this.endpoint, {
            method: 'GET',
            mode: 'same-origin',
            headers: { Accept: 'application/json' },
        })
        let data = await res.json()

        this._name = data.name
        for (let c of data.channels) this.channels.push(new Channel(c))
        for (let r of data.roles) this.roles.push(new Role(r))
    }

    async getChannels(): Promise<Channel[]> {
        await this.initialFetch
        return this.channels
    }

    async getRoles(): Promise<Role[]> {
        await this.initialFetch
        return this.roles
    }

    async data(dtype: string): Promise<D3Datum[]> {
        await this.initialFetch
        switch (dtype) {
            case 'channels':
                return this.channels
            case 'roles':
                return this.roles
            default:
                throw new Error(`No such data ${dtype} available`)
        }
    }
}
