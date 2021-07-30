// app.ts
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

import { selectAndMount } from '../../components/utils/app'
import CoreSettings from './CoreSettings.vue'
import ExtensionSettings from './ExtensionSettings.vue'
import ReadWriteAccessSettings from './ReadWriteAccessSettings.vue'

import { server } from '../../server'

window.addEventListener('DOMContentLoaded', () => {
    selectAndMount('#global-settings', CoreSettings)
    selectAndMount('#extension-settings', ExtensionSettings, {
        datasrc: '#extension-state',
    })
    selectAndMount('#read-write-access-settings', ReadWriteAccessSettings)
    document.querySelector('#sync-models')?.addEventListener('click', (ev) => {
        ev.preventDefault()
        server.updateModels()
    })
})
