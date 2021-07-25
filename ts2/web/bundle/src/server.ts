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
    ApolloQueryResult,
    FetchResult,
} from '@apollo/client/core'
import { setContext } from '@apollo/client/link/context'
import { onError } from '@apollo/client/link/error'
import { DocumentNode, stripIgnoredCharacters } from 'graphql'

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
    ServerACLQuery,
    ACLRoleModifier,
    ACLAction,
    AccessControlType,
    UpdateACLMutation,
    LoggingConfigQuery,
    UpdateLoggingMutation,
    UpdateLoggingMutationVariables,
    UpdatePermsMutation,
    UpdatePermsMutationVariables,
} from './@types/graphql/schema'

import SERVER_DETAILS from './graphql/query/server-details.graphql'
import BOT_DETAILS from './graphql/query/bot-details.graphql'
import UPDATE_PREFIX from './graphql/mutation/update-prefix.graphql'
import UPDATE_MODELS from './graphql/mutation/update-models.graphql'
import UPDATE_EXTENSIONS from './graphql/mutation/update-extensions.graphql'
import UPDATE_PERMS from './graphql/mutation/update-perms.graphql'

import LOGGING_CONFIG from './graphql/query/logging-config.graphql'
import UPDATE_LOGGING from './graphql/mutation/update-logging.graphql'

import SERVER_ACL from './graphql/query/server-acl.graphql'
import UPDATE_ACL from './graphql/mutation/update-acl.graphql'

import { omit, partition, pick } from 'lodash'

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
        let errors: Record<string, string> = {}
        for (let e of err.graphQLErrors) {
            errors[e.message] = e.name
        }
        for (let [msg, name] of Object.entries(errors)) {
            displayNotification(Color.DANGER, msg, name || 'Error', {
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
    readonly categoryId?: string

    constructor(
        data: Omit<ChannelType, 'guild' | 'category'> & {
            category?: Pick<ChannelType, 'snowflake'> | null
        }
    ) {
        this.id = data.snowflake!
        this.name = data.name!
        this.order = data.order!
        this.type = data.type!
        this.categoryId = data.category?.snowflake
    }

    public get content(): string {
        switch (this.type) {
            case ChannelEnum.text:
            case ChannelEnum.news:
                return `#${this.name}`
            default:
                return this.name
        }
    }

    public get foreground(): string {
        if (this.type === ChannelEnum.category) {
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
    readonly perms: string[]
    readonly color: number

    constructor(data: Omit<RoleType, 'guild'>) {
        this.id = data.snowflake
        this.name = data.name
        this.order = data.order
        this.perms = data.perms
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

export class ACL {
    public name: string
    public commands: string[]
    public channels: string[]
    public roles: string[]
    public modifier: ACLRoleModifier
    public action: ACLAction
    public error: string
    public deleted?: boolean = false

    constructor(data: AccessControlType) {
        this.name = data.name!
        this.commands = data.commands || []
        this.channels = data.channels || []
        this.roles = data.roles || []
        this.modifier = data.modifier
        this.action = data.action
        this.error = data.error || ''
    }

    static empty(): ACL {
        return new ACL({
            name: '',
            modifier: ACLRoleModifier.ANY,
            action: ACLAction.ENABLED,
        })
    }
}

export interface LoggingConfig {
    key: string
    name: string
    channel: string
    role: string
    superuser?: boolean
}

export type LoggingConfigSubmission = Omit<LoggingConfig, 'name' | 'superuser'>

interface QueryResults {
    serverInfo: ServerDetailsQuery
    loggingConf: LoggingConfigQuery
    botInfo: BotDetailsQuery
    aclInfo: ServerACLQuery
    [x: string]: any
}

const QUERIES: Record<keyof QueryResults, DocumentNode> = {
    serverInfo: SERVER_DETAILS,
    loggingConf: LOGGING_CONFIG,
    botInfo: BOT_DETAILS,
    aclInfo: SERVER_ACL,
}

class Server {
    private client: ApolloClient<NormalizedCacheObject>
    private queries: Partial<QueryResults> = {}

    private commands: Command[] = []

    private id: string
    private prefix: string | undefined

    private perms: string[] = []
    private readable: string[] = []
    private writable: string[] = []

    private channels: Channel[] = []
    private roles: Role[] = []
    private logging: LoggingConfig[] = []
    private acl: ACL[] = []

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
                op.variables.serverId = server
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

    async fetch<T, V = any>(
        query: DocumentNode,
        variables?: V
    ): Promise<ApolloQueryResult<T>> {
        return await this.client.query<T>({ query, variables })
    }

    async mutate<T, V = any>(
        mutation: DocumentNode,
        variables?: V
    ): Promise<FetchResult<T>> {
        return await this.client.mutate<T>({ mutation, variables })
    }

    async fetchQuery<K extends keyof QueryResults, T = QueryResults[K]>(
        key: K,
        refresh = false,
        variables?: Record<string, any>
    ): Promise<boolean> {
        let query = QUERIES[key]
        if (
            refresh ||
            !this.queries[key] ||
            !Object.keys(this.queries[key]).length
        ) {
            this.queries[key] = (
                await this.client.query<T>({ query, variables })
            ).data
            return true
        }
        return false
    }

    async fetchServerDetails(refresh = false): Promise<void> {
        let refreshed = await this.fetchQuery('serverInfo', refresh)
        if (refreshed) {
            let info = this.queries.serverInfo!.server!
            this.prefix = info.prefix
            this.perms = info.perms
            this.readable = info.readable
            this.writable = info.writable
            this.channels = info.channels
                .map((d) => new Channel(d))
                .sort((a, b) => a.order - b.order)
            this.roles = info.roles
                .map((d) => new Role(d))
                .sort((a, b) => a.order - b.order)
        }
    }

    async fetchBotDetails(refresh = false): Promise<void> {
        let refreshed = await this.fetchQuery('botInfo', refresh)
        if (refreshed) {
            this.commands = this.queries
                .botInfo!.bot!.commands!.map((d) => new Command(d!))
                .sort((a, b) => a.id.localeCompare(b.id))
        }
    }

    async fetchLoggingConfig(refresh = false): Promise<void> {
        let refreshed = await this.fetchQuery('loggingConf', refresh)
        if (refreshed) {
            this.logging = this.queries.loggingConf!.logging!.map((d) => ({
                key: d!.key!,
                name: d!.name!,
                channel: d!.channel || '',
                role: d!.role || '',
            }))
        }
    }

    async fetchACLRules(refresh = false): Promise<void> {
        let refreshed = await this.fetchQuery('aclInfo', refresh)
        if (refreshed) {
            this.acl = this.queries.aclInfo!.acl!.map((d) => new ACL(d!))
        }
    }

    async getPrefix(): Promise<string> {
        await this.fetchServerDetails()
        return this.prefix!
    }

    async getReadablePerms(): Promise<string[]> {
        await this.fetchServerDetails()
        return this.readable
    }

    async getWritablePerms(): Promise<string[]> {
        await this.fetchServerDetails()
        return this.writable
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

    async getACLs(): Promise<ACL[]> {
        await this.fetchACLRules()
        return this.acl
    }

    async getLogging(): Promise<LoggingConfig[]> {
        await this.fetchLoggingConfig()
        return this.logging
    }

    async setPrefix(prefix: string): Promise<void> {
        let data = await this.client.mutate<
            UpdatePrefixMutation,
            Partial<UpdatePrefixMutationVariables>
        >({
            mutation: UPDATE_PREFIX,
            variables: { prefix: prefix },
        })
        this.prefix = data.data?.updatePrefix?.server?.prefix!
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

    async setPerms(readable: string[], writable: string[]) {
        let res = await this.client.mutate<
            UpdatePermsMutation,
            Omit<UpdatePermsMutationVariables, 'serverId'>
        >({
            mutation: UPDATE_PERMS,
            variables: { readable, writable },
        })
        this.readable = res.data?.updatePerms?.server?.readable!
        this.writable = res.data?.updatePerms?.server?.writable!
    }

    async updateModels(): Promise<void> {
        await this.client.mutate({ mutation: UPDATE_MODELS })
    }

    async updateACLs(acls: ACL[]): Promise<ACL[]> {
        let [remove, update] = partition(acls, (d) => d.deleted)
        update = update.map((d) => omit(d, 'deleted'))
        let removeKeys = remove.map((d) => d.name)
        let res = await this.client.mutate<UpdateACLMutation>({
            mutation: UPDATE_ACL,
            variables: { names: removeKeys, changes: update },
        })
        return res.data!.updateACL!.acl!.map((d) => new ACL(d!))
    }

    async updateLogging(logging: LoggingConfigSubmission[]): Promise<void> {
        await this.client.mutate<
            UpdateLoggingMutation,
            Partial<UpdateLoggingMutationVariables>
        >({
            mutation: UPDATE_LOGGING,
            variables: {
                config: logging.map((conf) =>
                    pick(conf, ['key', 'channel', 'role'])
                ),
            },
        })
    }
}

export function init() {
    server = new Server(getServerEndpoint(), getServerID())
}
