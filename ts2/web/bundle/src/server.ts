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
    HttpLink,
    from as linkFrom,
    NormalizedCacheObject,
} from '@apollo/client/core'
import { setContext } from '@apollo/client/link/context'
import { getCSRF } from './utils/site'

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

class Server {
    private client?: ApolloClient<NormalizedCacheObject>

    constructor(endpoint: string | null) {
        if (endpoint) {
            this.client = new ApolloClient({
                cache: new InMemoryCache(),
                link: linkFrom([
                    setCSRFToken,
                    new HttpLink({
                        uri: endpoint,
                        useGETForQueries: true,
                    }),
                ]),
            })
        }
    }
}

export function init() {
    server = new Server(getServerEndpoint())
}
