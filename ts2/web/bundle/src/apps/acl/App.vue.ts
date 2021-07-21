import { defineComponent, ref } from 'vue'

import ACLList from './ACLList.vue'
import ACLInspect from './ACLInspect.vue'
import { dataDiscordModel } from '../../components/discord'
import { filterACL, testACL } from './ACLRule.vue'

export default defineComponent({
    components: {
        'acl-list': ACLList,
        'acl-inspect': ACLInspect,
    },
    setup() {
        const rulesApp = ref<InstanceType<typeof ACLList>>()
        return {
            rulesApp,
        }
    },
    data(): { inspectorState: boolean | undefined } {
        return {
            inspectorState: undefined,
        }
    },
    methods: {
        runInspector(selection: ReturnType<typeof dataDiscordModel>) {
            let { roles, commands, channels } = selection
            let command = Object.keys(commands)[0]
            let channel = Object.keys(channels)[0]
            let category = channels[channel].categoryId
            let rules = filterACL(
                this.rulesApp!.merged.filter((d) => !d.deleted),
                command,
                channel,
                category
            )
            this.inspectorState = testACL(rules, new Set(Object.keys(roles)))
        },
        clearInspector() {
            this.inspectorState = undefined
        },
    },
})
