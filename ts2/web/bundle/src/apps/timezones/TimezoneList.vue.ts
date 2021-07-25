// TimezoneList.vue.ts
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
import { format as formatTime, utcToZonedTime } from 'date-fns-tz'

import FormContainer from '../../components/input/FormContainer.vue'
import ItemSelect from '../../components/input/ItemSelect.vue'
import { Role, server } from '../../server'
import {
    RoleTimezoneType,
    ServerTimezonesQuery,
    UpdateTimezonesMutation,
    UpdateTimezonesMutationVariables,
} from '../../@types/graphql/schema'

import SERVER_TIMEZONES from '../../graphql/query/server-timezones.graphql'
import UPDATE_TIMEZONES from '../../graphql/mutation/update-timezones.graphql'
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'

import zones from './tz'

async function loadRoleTimezones(): Promise<RoleTimezoneType[]> {
    let res = await server.fetch<ServerTimezonesQuery>(SERVER_TIMEZONES)
    return res.data.timezones!.map((d) => d!)
}

async function saveRoleTimezones(
    toUpdate: Record<string, string>,
    toDelete: string[]
): Promise<RoleTimezoneType[]> {
    let res = await server.mutate<
        UpdateTimezonesMutation,
        Omit<UpdateTimezonesMutationVariables, 'serverId'>
    >(UPDATE_TIMEZONES, {
        toDelete: toDelete,
        toUpdate: Object.entries(toUpdate).map(([k, v]) => ({
            roleId: k,
            timezone: v,
        })),
    })
    return res.data!.updateTimezones!.timezones!.map((d) => d!)
}

export default defineComponent({
    components: { FormContainer, ItemSelect },
    props: {
        tzsrc: { type: String, required: true },
    },
    setup(props) {
        let roles: Ref<Record<string, Role>> = ref({})
        let orig: Ref<RoleTimezoneType[]> = ref([])
        let data: Ref<{ roles: string[]; zones: string[] }[]> = ref([])
        let roleIds: Set<string>

        let clocks: Ref<{ time: string; zone: string }[]> = ref([])
        let printClock = (tz: string): [string, string] => {
            let time = utcToZonedTime(Date.now(), tz)
            let [clock, zone] = formatTime(time, 'HH:mm:ss;zzzz', {
                timeZone: tz,
            }).split(';')
            return [clock, zone]
        }
        let updateClockAt = (index: number) => {
            let role = data.value[index]
            if (
                !role.zones ||
                !role.zones.length ||
                !role.roles ||
                !role.roles.length
            ) {
                clocks.value[index] = { time: '---', zone: '---' }
                return
            }
            let [tz] = role.zones
            let [time, zone] = printClock(tz)
            clocks.value[index] = { time, zone }
        }
        let updateClocks = () => {
            for (let i = 0; i < data.value.length; i++) updateClockAt(i)
        }

        let setInitialData = (fetched: RoleTimezoneType[]) => {
            data.value = []
            orig.value = []
            orig.value.push(...fetched)
            data.value.push(
                ...fetched.map((d) => ({
                    roles: [
                        roleIds.has(d.roleId)
                            ? d.roleId
                            : `deleted role ${d.roleId}`,
                    ],
                    zones: [d.timezone],
                }))
            )
            clocks.value = []
            updateClocks()
        }

        let loading = ref(true)
        onMounted(async () => {
            let [r, roleTimezones] = await Promise.all([
                server.getRoles(),
                loadRoleTimezones(),
            ])

            Object.assign(roles.value, ...r.map((r) => ({ [r.id]: r })))
            roleIds = new Set(Object.keys(roles.value))

            setInitialData(roleTimezones)
            updateClocks()
            setInterval(() => updateClocks(), 1000)
            loading.value = false
        })

        return {
            roles,
            zones,
            data,
            clocks,
            orig,
            loading,
            updateClockAt,
            setInitialData,
        }
    },
    data() {
        return { zones }
    },
    methods: {
        createTimezone() {
            this.data.push({ roles: [], zones: [] })
            this.clocks.push({ time: '---', zone: '---' })
        },
        async submit() {
            let toUpdate: Record<string, string> = {}
            let toDelete: Set<string> = new Set(this.orig.map((r) => r.roleId))
            for (let item of this.data) {
                if (
                    !item.roles ||
                    !item.zones ||
                    !item.roles.length ||
                    !item.zones.length
                )
                    continue
                let [zone] = item.zones
                for (let role of item.roles) {
                    toUpdate[role] = zone
                    toDelete.delete(role)
                }
            }
            let refreshed
            try {
                refreshed = await saveRoleTimezones(toUpdate, [...toDelete])
            } catch (e) {
                return
            }
            this.setInitialData(refreshed)
            displayNotification(Color.SUCCESS, 'Settings saved')
        },
    },
})
