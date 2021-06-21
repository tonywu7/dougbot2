// search.ts
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

import * as lunr from 'lunr'
import { slugify } from './util'

type Configurator = (a: lunr.Builder) => void

export interface SearchIndex {
    id: string
    [key: string]: string
}

export interface Indexable {
    getIndex(): SearchIndex
}

export class TextSearch<T extends Indexable> {
    private index: lunr.Index
    private items: Record<string, T> = {}

    constructor(collection: Iterable<T>, configurator: Configurator = () => {}) {
        let documents: Array<SearchIndex> = []
        let schema: Set<string> = new Set()
        for (let item of collection) {
            let idx = item.getIndex()
            documents.push(idx)
            this.items[idx.id] = item
            for (let k of Object.keys(idx)) schema.add(k)
        }
        this.index = lunr((builder) => {
            builder.ref('id')
            for (let k of schema) builder.field(k)
            configurator(builder)
            documents.forEach((d) => builder.add(d))
        })
    }

    public search(query: string): T[] {
        let indices = this.index.search(query).map((r) => r.ref)
        return this.values(indices)
    }

    public values(keys: Array<string>): T[] {
        let items = []
        for (let id of keys) items.push(this.items[id])
        return items
    }

    public get query(): (fn: lunr.Index.QueryBuilder) => lunr.Index.Result[] {
        return this.index.query.bind(this.index)
    }
}

export function configureAsPrefixSearch(builder: lunr.Builder): void {
    builder.pipeline.remove(lunr.stopWordFilter)
    builder.pipeline.remove(lunr.stemmer)
    builder.searchPipeline.remove(lunr.stopWordFilter)
    builder.searchPipeline.remove(lunr.stemmer)
}

export function allKeywords(keywords: string) {
    let tokens = lunr.tokenizer(slugify(keywords))
    return (q: lunr.Query) => {
        tokens.forEach((k) =>
            q.term(k, {
                wildcard: lunr.Query.wildcard.TRAILING,
                presence: lunr.Query.presence.REQUIRED,
            })
        )
    }
}
