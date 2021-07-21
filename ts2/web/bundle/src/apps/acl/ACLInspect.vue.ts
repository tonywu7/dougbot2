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
import { dataDiscordModel, setupDiscordModel } from '../../components/discord'
import ItemSelect from '../../components/input/ItemSelect.vue'

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
        return { ...setupDiscordModel() }
    },
    data() {
        let errors = { commands: '', channels: '' }
        return { errors, selected: dataDiscordModel() }
    },
    computed: {
        command(): string {
            return this.selected.commands[
                Object.keys(this.selected.commands)[0]
            ].content
        },
        channel(): string {
            return this.selected.channels[
                Object.keys(this.selected.channels)[0]
            ].content
        },
        channelColor(): { color: string } {
            return {
                color: this.selected.channels[
                    Object.keys(this.selected.channels)[0]
                ].foreground,
            }
        },
    },
    methods: {
        runTest() {
            this.errors = { commands: '', channels: '' }
            setTimeout(() => {
                let channels = this.selected.channels || {}
                let commands = this.selected.commands || {}
                if (!Object.keys(channels).length) {
                    this.errors.channels = 'Please choose a channel.'
                    return
                }
                if (!Object.keys(commands).length) {
                    this.errors.commands = 'Please choose a command.'
                    return
                }
                this.$emit('run-test', this.selected)
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
