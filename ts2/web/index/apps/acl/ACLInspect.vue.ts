// ACLInspect.vue.ts
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

import { defineComponent } from 'vue'
import { ChannelEnum } from '../../@types/graphql/schema'
import { setupDiscordModel } from '../../components/discord'
import ItemSelect from '../../components/input/ItemSelect.vue'
import { ACLTestOptions } from './ACLRule.vue'

export default defineComponent({
    components: { ItemSelect },
    props: {
        state: {
            type: Boolean,
            default: undefined,
        },
    },
    emits: ['run-test', 'clear'],
    setup() {
        return {
            ...setupDiscordModel(
                undefined,
                (c) =>
                    c.type == ChannelEnum.text || c.type == ChannelEnum.category
            ),
        }
    },
    data() {
        let errors = { command: '', channel: '' }
        let selected: {
            roles: string[]
            command: string | undefined
            channel: string | undefined
        } = { roles: [], command: undefined, channel: undefined }
        return { errors, selected }
    },
    computed: {
        command(): string {
            return this.commands[this.selected.command!].content
        },
        channel(): string {
            return this.channels[this.selected.channel!].content
        },
        channelColor(): { color: string } {
            return {
                color: this.channels[this.selected.channel!].foreground,
            }
        },
    },
    methods: {
        runTest() {
            this.errors = { command: '', channel: '' }
            setTimeout(() => {
                let channel = this.selected.channel
                let command = this.selected.command
                if (!this.selected.channel) {
                    this.errors.channel = 'Please choose a channel.'
                    return
                }
                if (!this.selected.command) {
                    this.errors.command = 'Please choose a command.'
                    return
                }
                channel = channel!
                command = command!
                let category = this.channels[channel].categoryId
                let payload: ACLTestOptions = {
                    roles: new Set(this.selected.roles),
                    category,
                    channel,
                    command,
                }
                this.$emit('run-test', payload)
            })
        },
    },
    watch: {
        selected: {
            handler() {
                this.$emit('clear')
            },
            deep: true,
        },
    },
})
