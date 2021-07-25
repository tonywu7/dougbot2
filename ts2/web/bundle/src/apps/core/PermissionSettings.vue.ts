// PermissionSettings.vue.ts
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

import { defineComponent, onBeforeMount, ref, Ref } from 'vue'

import ItemSelect, {
    ItemCandidate,
} from '../../components/input/ItemSelect.vue'
import FormContainer from '../../components/input/FormContainer.vue'

import { server } from '../../server'
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'

const PERMISSIONS: Record<string, { content: string; foreground: string }> = {
    administrator: { content: 'Administrator', foreground: '#7acc9c' },
    manage_channels: { content: 'Manage Channels', foreground: '#7acc9c' },
    manage_guild: { content: 'Manage Server', foreground: '#7acc9c' },
    view_audit_log: { content: 'View Audit Log', foreground: '#7acc9c' },
    manage_roles: { content: 'Manage Roles', foreground: '#ba6cd9' },
    manage_webhooks: { content: 'Manage Webhooks', foreground: '#ba6cd9' },
    manage_emojis: { content: 'Manage Emotes', foreground: '#ba6cd9' },
    kick_members: { content: 'Kick Members', foreground: '#6cadd9' },
    ban_members: { content: 'Ban Members', foreground: '#6cadd9' },
    view_guild_insights: {
        content: 'View Server Insights',
        foreground: '#6cadd9',
    },
    mute_members: { content: 'Mute Members', foreground: '#6cadd9' },
    manage_nicknames: { content: 'Manage Nicknames', foreground: '#6cadd9' },
    priority_speaker: { content: 'Priority Speaker', foreground: '#206694' },
    manage_messages: { content: 'Manage Messages', foreground: '#206694' },
    mention_everyone: {
        content: 'Mention @everyone, @here, and All Roles',
        foreground: '#206694',
    },
    deafen_members: { content: 'Deafen Members', foreground: '#206694' },
    move_members: { content: 'Move Members', foreground: '#206694' },
    create_instant_invite: {
        content: 'Create Invites',
        foreground: '#ffc107',
    },
    add_reactions: { content: 'Add Reactions', foreground: '#ffc107' },
    stream: { content: 'Stream', foreground: '#ffc107' },
    read_messages: { content: 'View Channels', foreground: '#ffc107' },
    send_messages: { content: 'Send Messages', foreground: '#ffc107' },
    send_tts_messages: { content: 'Send TTS Messages', foreground: '#ffc107' },
    embed_links: { content: 'Embed Links', foreground: '#ffc107' },
    attach_files: { content: 'Attach Files', foreground: '#ffc107' },
    read_message_history: {
        content: 'Read Message History',
        foreground: '#ffc107',
    },
    external_emojis: { content: 'Use External Emotes', foreground: '#ffc107' },
    connect: { content: 'Connect', foreground: '#ffc107' },
    speak: { content: 'Speak', foreground: '#ffc107' },
    use_voice_activation: {
        content: 'Use Voice Activation',
        foreground: '#ffc107',
    },
    change_nickname: { content: 'Change Nickname', foreground: '#ffc107' },
    use_slash_commands: {
        content: 'Use Slash Commands',
        foreground: '#ffc107',
    },
    request_to_speak: { content: 'Request To Speak', foreground: '#ffc107' },
}

const PERM_ITEMS: Record<string, ItemCandidate> = Object.assign(
    {},
    ...Object.entries(PERMISSIONS).map(([k, v]) => ({
        [k]: {
            id: k,
            ...v,
            getIndex() {
                return { id: k, name: v.content }
            },
        },
    }))
)

export default defineComponent({
    components: { ItemSelect, FormContainer },
    setup() {
        let readable: Ref<string[]> = ref([])
        let writable: Ref<string[]> = ref([])
        let loading: Ref<boolean> = ref(true)
        onBeforeMount(async () => {
            readable.value.push(...(await server.getReadablePerms()))
            writable.value.push(...(await server.getWritablePerms()))
            loading.value = false
        })
        return { readable, writable, loading }
    },
    data() {
        let permissions = PERM_ITEMS
        return {
            permissions,
            processing: false,
        }
    },
    computed: {
        buttonState(): Record<string, boolean> {
            return { disabled: this.processing }
        },
    },
    methods: {
        async submit() {
            try {
                await server.setPerms(this.readable, this.writable)
            } catch (e) {
                return
            }
            displayNotification(Color.SUCCESS, 'Permissions saved.')
        },
    },
})
