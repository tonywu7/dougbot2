// ExtensionSettings.vue.ts
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

import InputField from '../../components/input/InputField.vue'
import FormContainer from '../../components/input/FormContainer.vue'
import { server } from '../../server'
import { Color } from '../../components/modal/bootstrap'
import { displayNotification } from '../../components/utils/modal'

type ExtensionInfo = {
    id: string
    label: string
    enabled: boolean
}

export default defineComponent({
    components: { FormContainer, InputField },
    props: {
        datasrc: {
            type: String,
            required: true,
        },
    },
    setup(props) {
        let extensionElem = document.querySelector<HTMLElement>(props.datasrc)!
        let extensions: ExtensionInfo[] = []
        let values: Record<string, boolean> = {}
        extensionElem
            .querySelectorAll<HTMLElement>('.extension-label')
            .forEach((e) => {
                let id = e.dataset.id!
                let enabled = Boolean(e.dataset.enabled)
                let label = e.innerHTML
                extensions.push({ id, label, enabled })
                values[id] = enabled
            })
        return {
            extensions,
            values,
            initial: { ...values },
        }
    },
    data() {
        return {
            processing: false,
        }
    },
    methods: {
        getSubmittedValue(): string[] {
            return Object.entries(this.values)
                .filter(([k, v]) => v)
                .map(([k, v]) => k)
        },
        reset() {
            for (let [k, v] of Object.entries(this.values)) {
                this.initial[k] = v
            }
        },
        async submit() {
            this.processing = true
            try {
                await server.setExtensions(this.getSubmittedValue())
            } catch (e) {
                this.processing = false
                return
            }
            this.reset()
            displayNotification(Color.SUCCESS, 'Settings updated.')
            this.processing = false
        },
    },
})
