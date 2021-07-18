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
import { getCSRF } from './utils/site'

import { ServerInfoQuery, UpdatePrefixMutation } from './@types/graphql/schema'
import SERVER_INFO from './graphql/query/server-info.graphql'
import UPDATE_PREFIX from './graphql/mutation/update-prefix.graphql'

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

export function getServerEndpoint(): string | null {
    let elem = document.querySelector('[data-server-endpoint]')
    if (!elem) return null
    return (elem as HTMLElement).dataset.serverEndpoint!
}

export function getServerID(): string | null {
    let elem = document.querySelector('[data-server-id]')
    if (!elem) return null
    return (elem as HTMLElement).dataset.serverId!
}

class Server {
    private client: ApolloClient<NormalizedCacheObject>
    private serverInfo: ServerInfoQuery = {}

    constructor(endpoint: string | null, server: string | null) {
        let conf: ApolloClientOptions<NormalizedCacheObject> = {
            cache: new InMemoryCache(),
        }
        if (endpoint) {
            let http = new HttpLink({
                uri: endpoint,
                useGETForQueries: true,
            })
            let setServerPrefix = new ApolloLink((op, forward) => {
                op.variables.id = server
                return forward(op)
            })
            conf.link = linkFrom([setServerPrefix, setCSRFToken, http])
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
}

export function init() {
    server = new Server(getServerEndpoint(), getServerID())
}
