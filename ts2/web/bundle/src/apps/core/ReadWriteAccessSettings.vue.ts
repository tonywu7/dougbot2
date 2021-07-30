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
import { setupDiscordModel } from '../../components/discord'
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'

export default defineComponent({
    components: { ItemSelect, FormContainer },
    setup() {
        let readable: Ref<string[]> = ref([])
        let writable: Ref<string[]> = ref([])
        let loading: Ref<boolean> = ref(true)
        let { roles } = setupDiscordModel(async () => {
            readable.value.push(...(await server.getReadablePerms()))
            writable.value.push(...(await server.getWritablePerms()))
            loading.value = false
        })
        return { readable, writable, loading, roles }
    },
    data() {
        return {
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
