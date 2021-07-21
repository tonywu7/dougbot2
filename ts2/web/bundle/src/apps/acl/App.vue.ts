import { defineComponent, ref } from 'vue'

import ACLList from './ACLList.vue'
import ACLInspect from './ACLInspect.vue'
import { dataDiscordModel } from '../../components/discord'
import { ACLTestOptions, filterACL, testACL } from './ACLRule.vue'

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
        runInspector(options: ACLTestOptions) {
            let { roles, command, channel, category } = options
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
