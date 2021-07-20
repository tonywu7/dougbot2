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

import { defineComponent, onMounted, ref, Ref } from 'vue'
import ItemSelect from '../../components/input/ItemSelect.vue'
import { Role, Channel, Command, server } from '../../server'

export default defineComponent({
    components: { ItemSelect },
    setup() {
        let roles: Ref<Role[]> = ref([])
        let channels: Ref<Channel[]> = ref([])
        let commands: Ref<Command[]> = ref([])
        onMounted(async () => {
            roles.value.push(...(await server.getRoles()))
            channels.value.push(...(await server.getChannels()))
            commands.value.push(...(await server.getCommands()))
        })
        return { roles, channels, commands }
    },
    data() {
        let result: string = '...'
        let selected: {
            roles: Role[]
            channel: Channel[]
            command: Command[]
        } = { roles: [], channel: [], command: [] }
        return { result, selected }
    },
})
