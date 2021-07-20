// server.ts
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

import {
    ApolloClient,
    InMemoryCache,
    ApolloLink,
    HttpLink,
    from as linkFrom,
    NormalizedCacheObject,
    ApolloClientOptions,
} from '@apollo/client/core'
import { setContext } from '@apollo/client/link/context'
import { onError } from '@apollo/client/link/error'
import { getCSRF } from './utils/site'

import { displayNotification } from './components/utils/modal'
import { Color } from './components/modal/bootstrap'

import { ItemCandidate } from './components/input/ItemSelect.vue'
import { SearchIndex } from './utils/search'

import {
    ServerDetailsQuery,
    UpdatePrefixMutation,
    UpdatePrefixMutationVariables,
    UpdateExtensionsMutation,
    UpdateExtensionsMutationVariables,
    ChannelType,
    ChannelEnum,
    RoleType,
    BotDetailsQuery,
} from './@types/graphql/schema'

import SERVER_DETAILS from './graphql/query/server-details.graphql'
import BOT_DETAILS from './graphql/query/bot-details.graphql'
import UPDATE_PREFIX from './graphql/mutation/update-prefix.graphql'
import UPDATE_MODELS from './graphql/mutation/update-models.graphql'
import UPDATE_EXTENSIONS from './graphql/mutation/update-extensions.graphql'
import { stripIgnoredCharacters } from 'graphql'

export let server: Server

const setCSRFToken = setContext((request, previousContext) => {
    try {
        return {
            headers: { 'X-CSRFToken': getCSRF(document.documentElement) },
        }
    } catch (e) {
        return {}
    }
})

const notifyError = onError((err) => {
    if (err.networkError) {
        displayNotification(
            Color.WARNING,
            err.networkError.message || 'Network Error',
            err.networkError.name,
            {
                autohide: false,
            }
        )
    }
    if (err.graphQLErrors && err.graphQLErrors.length) {
        for (let e of err.graphQLErrors) {
            displayNotification(Color.DANGER, e.message, e.name || 'Error', {
                autohide: false,
            })
        }
    }
})

function stripQueryURL(uri: string): string {
    let url: URL
    try {
        url = new URL(uri)
    } catch (e) {
        url = new URL(uri, window.location.origin)
    }
    let query = url.searchParams.get('query')
    if (!query) return uri
    url.searchParams.set('query', stripIgnoredCharacters(query))
    if (url.origin == window.location.origin) {
        return url.toString().slice(url.origin.length)
    } else {
        return url.toString()
    }
}

function getServerEndpoint(): string | null {
    let elem = document.querySelector('[data-server-endpoint]')
    if (!elem) return null
    return (elem as HTMLElement).dataset.serverEndpoint!
}

function getServerID(): string | null {
    let elem = document.querySelector('[data-server-id]')
    if (!elem) return null
    return (elem as HTMLElement).dataset.serverId!
}

export class Command implements ItemCandidate {
    readonly id: string
    readonly content: string
    readonly foreground = '#d3d3d3'

    constructor(cmd: string) {
        this.id = this.content = cmd
    }

    public getIndex() {
        return { id: this.id }
    }
}

export class Channel implements ItemCandidate {
    readonly id: string
    readonly name: string
    readonly order: number
    readonly type: ChannelEnum

    constructor(data: Omit<ChannelType, 'guild'>) {
        this.id = data.snowflake!
        this.name = data.name!
        this.order = data.order!
        this.type = data.type!
    }

    public get content(): string {
        switch (this.type) {
            case ChannelEnum.Text:
            case ChannelEnum.News:
                return `#${this.name}`
            default:
                return this.name
        }
    }

    public get foreground(): string {
        if (this.type === ChannelEnum.Category) {
            return '#d3d3d3'
        }
        return '#7289da' // bring back blurple
    }

    public getIndex() {
        return {
            id: this.id,
            name: this.content,
            type: this.type,
        }
    }
}

export class Role implements ItemCandidate {
    readonly id: string
    readonly name: string
    readonly order: number
    readonly perms: number
    readonly color: number

    constructor(data: Omit<RoleType, 'guild'>) {
        this.id = data.snowflake
        this.name = data.name
        this.order = data.order
        this.perms = Number(data.perms)
        this.color = data.color || 0x7289da
    }

    public get content() {
        return this.name
    }

    public get foreground() {
        return `#${this.color.toString(16).padStart(6, '0')}`
    }

    getIndex(): SearchIndex {
        return {
            id: this.id,
            name: this.name,
        }
    }
}

class Server {
    private client: ApolloClient<NormalizedCacheObject>

    private id: string

    private serverInfo: ServerDetailsQuery = {}
    private botInfo: BotDetailsQuery = {}

    private channels: Channel[] = []
    private roles: Role[] = []

    private commands: Command[] = []

    constructor(endpoint: string | null, server: string | null) {
        this.id = server || ''

        let conf: ApolloClientOptions<NormalizedCacheObject> = {
            cache: new InMemoryCache(),
        }

        if (endpoint) {
            let http = new HttpLink({
                uri: endpoint,
                useGETForQueries: true,
                fetch: (input, init): Promise<Response> => {
                    return fetch(stripQueryURL(input.toString()), init)
                },
            })
            let setServerPrefix = new ApolloLink((op, forward) => {
                op.variables.itemId = server
                return forward(op)
            })
            conf.link = linkFrom([
                setServerPrefix,
                setCSRFToken,
                notifyError,
                http,
            ])
        }

        this.client = new ApolloClient(conf)
    }

    async fetchServerDetails(refresh = false): Promise<void> {
        if (refresh || !Object.keys(this.serverInfo).length) {
            this.serverInfo = (
                await this.client.query<ServerDetailsQuery>({
                    query: SERVER_DETAILS,
                })
            ).data
            this.channels = this.serverInfo
                .server!.channels.map((d) => new Channel(d))
                .sort((a, b) => a.order - b.order)
            this.roles = this.serverInfo
                .server!.roles.map((d) => new Role(d))
                .sort((a, b) => a.order - b.order)
        }
    }

    async fetchBotDetails(refresh = false): Promise<void> {
        if (refresh || !Object.keys(this.botInfo).length) {
            this.botInfo = (
                await this.client.query<BotDetailsQuery>({
                    query: BOT_DETAILS,
                })
            ).data
            this.commands = this.botInfo
                .bot!.commands!.map((d) => new Command(d!))
                .sort((a, b) => a.id.localeCompare(b.id))
        }
    }

    async getPrefix(): Promise<string> {
        await this.fetchServerDetails()
        return this.serverInfo.server!.prefix!
    }

    async getChannels(): Promise<Channel[]> {
        await this.fetchServerDetails()
        return this.channels
    }

    async getRoles(): Promise<Role[]> {
        await this.fetchServerDetails()
        return this.roles
    }

    async getCommands(): Promise<Command[]> {
        await this.fetchBotDetails()
        return this.commands
    }

    async setPrefix(prefix: string): Promise<void> {
        await this.client.mutate<
            UpdatePrefixMutation,
            Partial<UpdatePrefixMutationVariables>
        >({
            mutation: UPDATE_PREFIX,
            variables: { prefix: prefix },
        })
    }

    async setExtensions(extensions: string[]): Promise<void> {
        await this.client.mutate<
            UpdateExtensionsMutation,
            Partial<UpdateExtensionsMutationVariables>
        >({
            mutation: UPDATE_EXTENSIONS,
            variables: { extensions: extensions },
        })
    }

    async updateModels(): Promise<void> {
        await this.client.mutate({ mutation: UPDATE_MODELS })
    }
}

export function init() {
    server = new Server(getServerEndpoint(), getServerID())
}
