// discord.ts
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

import { Ref, ref, onMounted } from 'vue'
import { Role, Channel, Command, server } from '../server'

export function setupDiscordModel(
    onModelLoaded: () => Promise<void> = () => Promise.resolve()
) {
    let roles: Ref<Record<string, Role>> = ref({})
    let channels: Ref<Record<string, Channel>> = ref({})
    let commands: Ref<Record<string, Command>> = ref({})
    onMounted(async () => {
        Object.assign(
            roles.value,
            ...(await server.getRoles()).map((d) => ({ [d.id]: d }))
        )
        Object.assign(
            channels.value,
            ...(await server.getChannels()).map((d) => ({ [d.id]: d }))
        )
        Object.assign(
            commands.value,
            ...(await server.getCommands()).map((d) => ({ [d.id]: d }))
        )
        await onModelLoaded()
    })
    return { roles, channels, commands }
}

export function dataDiscordModel() {
    return { roles: {}, channels: {}, commands: {} } as {
        roles: Record<string, Role>
        channels: Record<string, Channel>
        commands: Record<string, Command>
    }
}
