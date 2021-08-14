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
import { textChannels } from 'web/components/discord'

import { Channel, Emote, Role, server } from 'web/server'

import {
    DeleteSuggestChannelsMutation,
    DeleteSuggestChannelsMutationVariables,
    SuggestChannelsQuery,
    SuggestionChannelInput,
    SuggestionChannelType,
    UpdateSuggestChannelsMutation,
    UpdateSuggestChannelsMutationVariables,
} from './@types/graphql/schema'
import SUGGEST_CHANNELS from './graphql/query/suggest-channels.graphql'
import DELETE_SUGGEST_CHANNELS from './graphql/mutation/delete-suggest-channels.graphql'
import UPDATE_SUGGEST_CHANNELS from './graphql/mutation/update-suggest-channels.graphql'
import {
    KeyValuePairInput,
    KeyValuePairType,
} from '../../../../internet/web/apps/timezones/@types/graphql/schema'
import { Color } from 'web/components/modal/bootstrap'
import { displayNotification } from 'web/components/utils/modal'

class Reaction {
    emote: string | null = null
    message: string = ''

    static fromKeyValuePair(kvp: KeyValuePairType) {
        let r = new Reaction()
        r.emote = kvp.key
        r.message = kvp.value
        return r
    }

    toKeyValuePair(): KeyValuePairInput | null {
        let emote = this.emote
        if (!emote) return null
        return { key: emote, value: this.message }
    }
}

class SuggestChannel {
    public _reactions: Reaction[] = []

    public channel: string | null
    public upvote: string | null
    public downvote: string | null
    public title: string
    public description: string
    public requiresText: boolean
    public requiresUploads: number
    public requiresLinks: number
    public arbiters: string[]

    constructor(data: Partial<SuggestionChannelType>) {
        this._reactions.push(
            ...(data.reactions
                ? data.reactions.map(Reaction.fromKeyValuePair)
                : [])
        )
        this.channel = data.channelId || null
        this.title = data.title || ''
        this.description = data.description || ''
        this.upvote = data.upvote || null
        this.downvote = data.downvote || null
        this.requiresText = data.requiresText === undefined || data.requiresText
        this.requiresUploads = data.requiresUploads || 0
        this.requiresLinks = data.requiresLinks || 0
        this.arbiters = data.arbiters || []
    }

    public get channelId(): string {
        return this.channel!
    }

    public get reactions(): KeyValuePairInput[] {
        let reactions: KeyValuePairInput[] = []
        for (let r of this._reactions) {
            let kvp = r.toKeyValuePair()
            if (kvp) reactions.push(kvp)
        }
        return reactions
    }

    public toJSON(): SuggestionChannelInput {
        return {
            channelId: this.channelId,
            upvote: this.upvote!,
            downvote: this.downvote!,
            title: this.title,
            description: this.description,
            requiresText: this.requiresText,
            requiresLinks: this.requiresLinks,
            requiresUploads: this.requiresUploads,
            arbiters: this.arbiters,
            reactions: this.reactions,
        }
    }
}

async function loadChannels(): Promise<SuggestChannel[]> {
    let res = await server.fetch<SuggestChannelsQuery>(SUGGEST_CHANNELS)
    return res.data.suggestChannels!.map((d) => new SuggestChannel(d!))
}

async function updateChannels(
    channels: SuggestChannel[]
): Promise<SuggestChannel[]> {
    let res = await server.mutate<
        UpdateSuggestChannelsMutation,
        Omit<UpdateSuggestChannelsMutationVariables, 'serverId'>
    >(UPDATE_SUGGEST_CHANNELS, {
        channels: channels.map((d) => d.toJSON()),
    })
    return res.data!.updateSuggestChannels!.channels!.map(
        (d) => new SuggestChannel(d!)
    )
}

async function deleteChannels(channelIds: string[]): Promise<boolean> {
    let res = await server.mutate<
        DeleteSuggestChannelsMutation,
        Omit<DeleteSuggestChannelsMutationVariables, 'serverId'>
    >(DELETE_SUGGEST_CHANNELS, {
        channelIds: channelIds,
    })
    return res.data!.deleteSuggestChannels!.successful
}

export default defineComponent({
    components: { FormContainer, ItemSelect, InputField },
    setup() {
        let loading = ref(true)

        let channels: Ref<Record<string, Channel>> = ref({})
        let roles: Ref<Record<string, Role>> = ref({})
        let emotes: Ref<Record<string, Emote>> = ref({})

        let data: Ref<SuggestChannel[]> = ref([])

        let index: Ref<number> = ref(0)
        let errors: Ref<string[]> = ref([])

        onMounted(async () => {
            let [ch, rl, em, dt] = await Promise.all([
                server.getChannels(),
                server.getRoles(),
                server.getEmotes(),
                loadChannels(),
            ])
            Object.assign(channels.value, ...ch.map((c) => ({ [c.id]: c })))
            Object.assign(roles.value, ...rl.map((r) => ({ [r.id]: r })))
            Object.assign(emotes.value, ...em.map((e) => ({ [e.id]: e })))
            channels.value = textChannels(channels.value)
            data.value.push(...dt)
            loading.value = false
        })

        return {
            loading,
            channels,
            roles,
            emotes,
            data,
            index,
            errors,
        }
    },
    data() {
        return {
            willDelete: false,
        }
    },
    computed: {
        error: {
            get(): string {
                return this.errors[this.index]
            },
            set(e: string) {
                this.errors[this.index] = e
            },
        },
        hasError(): boolean {
            return !!this.error && this.error.length > 0
        },
        current(): SuggestChannel | undefined {
            return this.data[this.index]
        },
    },
    methods: {
        activate(idx: number) {
            this.index = idx
            this.willDelete = false
        },
        display(idx: number): string {
            let ch = this.data[idx]
            let channel: Channel = this.channels[ch.channelId]
            if (channel) {
                return channel.name
            } else if (ch.channelId) {
                return ch.channelId
            } else {
                return '(channel unspecified)'
            }
        },
        createChannel() {
            let ch = new SuggestChannel({
                upvote: '🔼',
                downvote: '🔽',
                reactions: [
                    { key: '✅', value: 'approved' },
                    { key: '🚫', value: 'rejected' },
                ],
            })
            this.data.push(ch)
            this.activate(this.data.length - 1)
        },
        removeReaction(idx: number) {
            this.current?._reactions.splice(idx, 1)
        },
        addReaction() {
            this.current?._reactions.push(new Reaction())
        },
        async submit() {
            if (!this.current?.channelId) {
                this.error = 'You must specify a channel.'
                return
            }
            let result
            try {
                result = await updateChannels([this.current])
            } catch (e) {
                return
            }
            displayNotification(Color.SUCCESS, 'Settings saved')
        },
        async remove() {
            if (this.current?.channelId) {
                let name = this.display(this.index)
                try {
                    await deleteChannels([this.current.channelId])
                } catch (e) {
                    return
                }
                displayNotification(
                    Color.SUCCESS,
                    `Suggestion channel ${name} deleted`
                )
            }
            this.data.splice(this.index, 1)
            this.activate(0)
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
