// ACLList.vue.ts
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
import ACLRule from './ACLRule.vue'

import { ACL, server } from '../../server'
import { displayNotification } from '../../components/utils/modal'
import { Color } from '../../components/modal/bootstrap'

export default defineComponent({
    components: { 'acl-rule': ACLRule },
    emits: ['update:data'],
    setup() {
        let rules: Ref<ACL[]> = ref([])
        let loading = ref(true)
        onMounted(async () => {
            rules.value.push(...(await server.getACLs()))
            loading.value = false
        })
        return { rules, loading }
    },
    data(): {
        changed: ACL[]
        created: ACL[]
    } {
        return {
            changed: [],
            created: [],
        }
    },
    computed: {
        merged(): ACL[] {
            let base: ACL[] = [...this.rules]
            base.push(...this.created)
            for (let i = 0; i < this.changed.length; i++) {
                let item = this.changed[i]
                if (item !== undefined) base[i] = item
            }
            return base
        },
    },
    methods: {
        untitled(): string {
            let i = 1
            while (
                new Set(this.merged.map((d) => d.name)).has(
                    `untitled rule (${i})`
                )
            )
                i++
            return `untitled rule (${i})`
        },
        createRule(): void {
            let rule = ACL.empty()
            let name = this.untitled()
            rule.name = name
            this.created.push(rule)
            this.$emit('update:data')
        },
        updateRule(item: ACL, index: number) {
            this.changed[index] = item
            this.$emit('update:data')
        },
        assertUniqueNames(items: ACL[]): void {
            let names: Set<string> = new Set()
            for (let rule of items) {
                if (rule.deleted) continue
                if (names.has(rule.name)) {
                    throw new Error(
                        `Different rules cannot have the same name: ${rule.name}`
                    )
                }
                names.add(rule.name)
            }
        },
        async submit() {
            let items = this.merged
            try {
                this.assertUniqueNames(items)
            } catch (e) {
                displayNotification(Color.WARNING, e.toString())
                return
            }
            for (let i = 0; i < this.rules.length; i++) {
                let before = this.rules[i]
                let after = this.changed[i]
                if (after !== undefined && before.name !== after.name) {
                    items.push(Object.assign({}, before, { deleted: true }))
                }
            }
            try {
                let data = await server.updateACLs(items)
                displayNotification(Color.SUCCESS, 'Rules saved.')
                this.rules = data
                this.created.length = 0
                this.changed.length = 0
            } catch (e) {
                console.warn(e)
            }
        },
    },
})
