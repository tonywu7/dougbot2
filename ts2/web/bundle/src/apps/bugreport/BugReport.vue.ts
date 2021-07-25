// BugReport.vue.ts
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
import FormContainer from '../../components/input/FormContainer.vue'
import InputSelect, {
    InputSelectOption,
} from '../../components/input/InputSelect.vue'
import InputField from '../../components/input/InputField.vue'
import CSRFToken from '../../components/input/CSRFToken.vue'

const COMMAND_ISSUE = `\
Issues such as command errors or bot malfunctions.
Describe what you did when the problem happened, \
what you expected the bot to do, and what the error did the bot show.
`
const DOCUMENTATION_ISSUE = `\
Wrong information or grammar mistakes.
`
const WEBSITE_ISSUE = `\
Layout & formatting issues, script errors, or network errors.
`

export default defineComponent({
    components: {
        FormContainer,
        InputSelect,
        InputField,
        'csrf-token': CSRFToken,
    },
    props: { action: { type: String, required: true } },
    data() {
        let reportTypes: InputSelectOption<number>[] = [
            { value: 0, text: '(choose an option)' },
            { value: 1, text: 'Command issues' },
            { value: 2, text: 'Documentation errors' },
            { value: 3, text: 'Website issues' },
            { value: 4, text: 'Other feedback' },
        ]
        let topic: keyof typeof reportTypes = 0
        let summary: string = ''
        let path: string = ''
        return { reportTypes, topic, summary, path }
    },
    computed: {
        summaryHint(): string | undefined {
            return {
                0: undefined,
                1: COMMAND_ISSUE,
                2: DOCUMENTATION_ISSUE,
                3: WEBSITE_ISSUE,
                4: '',
            }[this.topic]
        },
        pathLabel(): string | undefined {
            return {
                0: undefined,
                1: 'The command you used, if any',
                2: undefined,
                3: 'The URL of the page with the issue, if any',
                4: undefined,
            }[this.topic]
        },
    },
})
