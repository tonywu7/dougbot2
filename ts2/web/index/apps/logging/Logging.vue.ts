// Logging.vue.ts
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

import { defineComponent, PropType, Ref, ref } from 'vue'
import {
    Channel,
    LoggingConfig,
    LoggingConfigSubmission,
    server,
} from '../../server'

import FormContainer from '../../components/input/FormContainer.vue'
import ItemSelect from '../../components/input/ItemSelect.vue'
import { setupDiscordModel, textChannels } from '../../components/discord'
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'

type LoggingSelection = {
    role: string | undefined
    channel: string | undefined
}

export default defineComponent({
    components: { FormContainer, ItemSelect },
    props: {
        conf: {
            type: Object as PropType<LoggingConfig[]>,
            required: true,
        },
    },
    setup(props) {
        let settings: Ref<LoggingConfig[]> = ref([])
        let logging: Ref<Record<string, LoggingSelection>> = ref(
            Object.assign(
                {},
                ...props.conf.map((c) => ({
                    [c.key]: { role: undefined, channel: undefined },
                }))
            )
        )
        let { roles, channels } = setupDiscordModel(async () => {
            settings.value.push(...(await server.getLogging()))
            for (let c of settings.value) {
                let conf = logging.value[c.key]
                conf.channel = c.channel
                conf.role = c.role
            }
            loading.value = false
        })
        let loading = ref(true)
        return { settings, roles, channels, loading, logging }
    },
    computed: {
        textChannels(): Record<string, Channel> {
            return textChannels(this.channels)
        },
    },
    methods: {
        async submit() {
            let existing = new Set(this.settings.map((d) => d.key))
            let finalized: LoggingConfigSubmission[] = []
            for (let [k, v] of Object.entries(this.logging)) {
                let channel = v.channel
                let role = v.role
                if (!channel) {
                    if (existing.has(k)) {
                        finalized.push({ key: k, channel: '', role: '' })
                    } else {
                        continue
                    }
                } else {
                    role = role || ''
                    finalized.push({ key: k, channel, role })
                }
            }
            try {
                await server.updateLogging(finalized)
            } catch (e) {
                return
            }
            displayNotification(Color.SUCCESS, 'Settings saved.')
        },
    },
})
