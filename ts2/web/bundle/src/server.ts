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

import { ServerInfoQuery, UpdatePrefixMutation } from './@types/graphql/schema'
import SERVER_INFO from './graphql/query/server-info.graphql'
import UPDATE_PREFIX from './graphql/mutation/update-prefix.graphql'
import UPDATE_MODELS from './graphql/mutation/update-models.graphql'

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

class Server {
    private client: ApolloClient<NormalizedCacheObject>
    private id: string
    private serverInfo: ServerInfoQuery = {}

    constructor(endpoint: string | null, server: string | null) {
        this.id = server || ''

        let conf: ApolloClientOptions<NormalizedCacheObject> = {
            cache: new InMemoryCache(),
        }

        let notifyError = onError((err) => {
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
                    displayNotification(
                        Color.DANGER,
                        e.message,
                        e.name || 'Error',
                        {
                            autohide: false,
                        }
                    )
                }
            }
        })

        if (endpoint) {
            let http = new HttpLink({
                uri: endpoint,
                useGETForQueries: true,
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

    async fetchServerInfo(refresh = false): Promise<void> {
        if (refresh || !Object.keys(this.serverInfo).length) {
            this.serverInfo = (
                await this.client.query<ServerInfoQuery>({
                    query: SERVER_INFO,
                })
            ).data
        }
    }

    async getPrefix(): Promise<string> {
        await this.fetchServerInfo()
        return this.serverInfo.server!.prefix!
    }

    async setPrefix(prefix: string): Promise<void> {
        await this.client.mutate<UpdatePrefixMutation>({
            mutation: UPDATE_PREFIX,
            variables: { prefix: prefix },
        })
    }

    async updateModels(): Promise<void> {
        await this.client.mutate({ mutation: UPDATE_MODELS })
    }
}

export function init() {
    server = new Server(getServerEndpoint(), getServerID())
}
