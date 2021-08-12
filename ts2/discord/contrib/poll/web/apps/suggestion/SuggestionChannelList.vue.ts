// SuggestionChannel.vue.ts
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

import { defineComponent, onMounted, Ref, ref } from 'vue'

import FormContainer from 'web/components/input/FormContainer.vue'
import ItemSelect, { ItemCandidate } from 'web/components/input/ItemSelect.vue'
import InputField from 'web/components/input/InputField.vue'

import { Channel, Emote, server } from 'web/server'
import {
    SuggestionChannelInput,
    SuggestionChannelType,
} from 'web/@types/graphql/schema'
import { textChannels } from 'web/components/discord'

import {
    ApplySuggestChannelsMutation,
    ApplySuggestChannelsMutationVariables,
    SuggestChannelsQuery,
} from './@types/graphql/schema'
import SUGGEST_CHANNELS from './graphql/query/suggest-channels.graphql'
import APPLY_SUGGEST_CHANNELS from './graphql/mutation/apply-suggest-channels.graphql'

class SuggestChannel {
    private _channels: string[] = []
    private _upvotes: string[] = []
    private _downvotes: string[] = []
    private _approves: string[] = []
    private _rejects: string[] = []
    public description: string
    public requiresText: boolean
    public requiresUploads: number
    public requiresLinks: number

    constructor(data: Partial<SuggestionChannelType>) {
        this._channels.push(...(data.channelId ? [data.channelId] : []))
        this._upvotes.push(...(data.upvote ? [data.upvote] : []))
        this._downvotes.push(...(data.downvote ? [data.downvote] : []))
        this._approves.push(...(data.approve ? [data.approve] : []))
        this._rejects.push(...(data.reject ? [data.reject] : []))
        this.description = data.description || ''
        this.requiresText = data.requiresText === undefined || data.requiresText
        this.requiresUploads = data.requiresUploads || 0
        this.requiresLinks = data.requiresLinks || 0
    }

    public get channelId(): string {
        return this._channels[0]
    }

    public get upvote(): string {
        return this._upvotes[0] || ''
    }

    public get downvote(): string {
        return this._downvotes[0] || ''
    }

    public get approve(): string {
        return this._approves[0] || ''
    }

    public get reject(): string {
        return this._rejects[0] || ''
    }

    public toJSON(): SuggestionChannelInput {
        return {
            channelId: this.channelId!,
            upvote: this.upvote,
            downvote: this.downvote,
            approve: this.approve,
            reject: this.reject,
            description: this.description,
            requiresText: this.requiresText,
            requiresLinks: this.requiresLinks,
            requiresUploads: this.requiresUploads,
        }
    }
}

async function loadChannels(): Promise<SuggestChannel[]> {
    let res = await server.fetch<SuggestChannelsQuery>(SUGGEST_CHANNELS)
    return res.data.suggestChannels!.map((d) => new SuggestChannel(d!))
}

async function saveChannels(
    toDelete: string[],
    toUpdate: SuggestChannel[]
): Promise<SuggestChannel[]> {
    let res = await server.mutate<
        ApplySuggestChannelsMutation,
        Omit<ApplySuggestChannelsMutationVariables, 'serverId'>
    >(APPLY_SUGGEST_CHANNELS, {
        deleted: toDelete,
        updated: toUpdate,
    })
    return res.data!.updateSuggestChannels!.channels!.map(
        (d) => new SuggestChannel(d!)
    )
}

export default defineComponent({
    components: { FormContainer, ItemSelect, InputField },
    setup() {
        let loading = ref(true)
        let initial: string[] = []
        let channels: Ref<Record<string, Channel>> = ref({})
        let emotes: Ref<Record<string, Emote>> = ref({})
        let data: Ref<SuggestChannel[]> = ref([])
        onMounted(async () => {
            let [ch, em, dt] = await Promise.all([
                server.getChannels(),
                server.getEmotes(),
                loadChannels(),
            ])
            Object.assign(channels.value, ...ch.map((c) => ({ [c.id]: c })))
            Object.assign(emotes.value, ...em.map((e) => ({ [e.id]: e })))
            channels.value = textChannels(channels.value)
            data.value.push(...dt)
            initial.push(...dt.map((d) => d.channelId!))
            loading.value = false
        })
        return {
            initial,
            loading,
            channels,
            emotes,
            data,
        }
    },
    data() {
        return {
            _expanded: -1,
        }
    },
    methods: {
        createChannel() {
            this.data.push(
                new SuggestChannel({
                    upvote: '🔼',
                    downvote: '🔽',
                    approve: '✅',
                    reject: '🚫',
                })
            )
        },
        async submit() {
            let deleted: Set<string> = new Set(this.initial)
            let changed: SuggestChannel[] = []
            for (let item of this.data) {
                if (item.channelId) {
                    deleted.delete(item.channelId)
                    changed.push(item)
                }
            }
            let result = await saveChannels([...deleted], changed)
            this.initial = result.map((c) => c.channelId)
            this.data = [...result]
        },
        expanded(i: number) {
            return this._expanded === i
        },
        setExpanded(i: number) {
            if (this._expanded === i) {
                this._expanded = -1
            } else {
                this._expanded = i
            }
        },
        emoteFactory(search: string): ItemCandidate {
            return {
                id: search,
                content: search,
                foreground: '#7289da',
                background: '#00000000',
                getIndex: () => ({
                    id: search,
                }),
            }
        },
    },
})
