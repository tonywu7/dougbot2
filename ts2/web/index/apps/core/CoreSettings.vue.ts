// CoreSettings.vue.ts
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
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'

interface ComponentData {
    original: string
    value: string
    error?: string
    processing: boolean
}

export default defineComponent({
    components: { FormContainer, InputField },
    props: {
        prefix: { type: String, required: true },
    },
    data(): ComponentData {
        return {
            original: this.prefix,
            value: this.prefix,
            error: undefined,
            processing: false,
        }
    },
    computed: {
        buttonState(): Record<string, boolean> {
            return { disabled: this.processing || Boolean(this.error) }
        },
    },
    methods: {
        async submit() {
            this.processing = true
            try {
                await server.setPrefix(this.value)
            } catch (e) {
                this.processing = false
                return
            }
            this.original = this.value
            displayNotification(Color.SUCCESS, 'Settings updated.')
            this.processing = false
        },
        validate(v: string): string | undefined {
            if (!v || !v.length) {
                return 'Prefix cannot be empty.'
            }
        },
    },
})
