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

import { defineComponent, PropType } from 'vue'

import ItemSelect from '../../components/input/ItemSelect.vue'
import InputSelect from '../../components/input/InputSelect.vue'
import InputField from '../../components/input/InputField.vue'

import { InputSelectOption } from '../../components/input/InputSelect.vue'
import { setupDiscordModel } from '../../components/discord'
import {
    ACLAction,
    ACLRoleModifier,
    ChannelEnum,
} from '../../@types/graphql/schema'
import { ACL } from '../../server'
import { slugify } from '../../utils/data'

const aclModifiers: InputSelectOption<ACLRoleModifier>[] = [
    {
        text: 'has none of roles',
        value: ACLRoleModifier.NONE,
    },
    {
        text: 'has any of roles',
        value: ACLRoleModifier.ANY,
    },
    {
        text: 'has all of roles',
        value: ACLRoleModifier.ALL,
    },
]

const aclActions: InputSelectOption<ACLAction>[] = [
    {
        text: 'commands are disabled',
        value: ACLAction.DISABLED,
    },
    {
        text: 'commands are enabled',
        value: ACLAction.ENABLED,
    },
]

type Specificity = [number, number, number, number]

export interface ACLRuleComponentOption {}

export function aclSpecificity(rule: ACL): Specificity {
    let mod = rule.modifier
    let roles = rule.roles
    let channels = rule.channels
    let commands = rule.commands
    return [
        Number(mod === ACLRoleModifier.NONE) && roles.length,
        Number(mod === ACLRoleModifier.ALL) && roles.length,
        Number(mod === ACLRoleModifier.ANY) && Number(roles.length > 0),
        (Number(Boolean(channels.length)) << 1) +
            (Number(Boolean(commands.length)) << 0),
    ]
}

function dictorder<T extends number>(a: T[], b: T[]): number {
    for (let i = 0; i < Math.min(a.length, b.length); i++) {
        let d = a[i] - b[i]
        if (d) return d
    }
    return 0
}

export function filterACL(
    rules: ACL[],
    command: string,
    channel: string,
    category?: string
): ACL[] {
    return rules.filter(
        (r) =>
            (!r.commands.length || r.commands.includes(command)) &&
            (!r.channels.length ||
                r.channels.includes(channel) ||
                (category && r.channels.includes(category)))
    )
}

function aclApplicable(r: ACL, roles: Set<string>) {
    let target = new Set(r.roles)
    let applicable = !r.roles.length
    if (!applicable) {
        if (r.modifier === ACLRoleModifier.NONE) {
            applicable = ![...target].filter((x) => roles.has(x)).length
        } else if (r.modifier === ACLRoleModifier.ANY) {
            applicable = Boolean([...target].filter((x) => roles.has(x)).length)
        } else {
            applicable = [...target].every((x) => roles.has(x))
        }
    }
    return applicable
}

export function testACL(rules: ACL[], roles: Set<string>): boolean {
    let bucketmap: Record<string, [Specificity, ACL[]]> = {}
    for (let r of rules) {
        let s = aclSpecificity(r)
        let k = s.toString()
        let b = bucketmap[k]
        if (!b) {
            bucketmap[k] = [s, [r]]
        } else {
            b[1].push(r)
        }
    }
    let buckets: [Specificity, ACL[]][] = Object.values(bucketmap).sort(
        (a, b) => -dictorder(a[0], b[0])
    )
    for (let [level, tests] of buckets) {
        tests = tests.filter((t) => aclApplicable(t, roles))
        if (!tests.length) continue
        if (tests.some((r) => r.action === ACLAction.ENABLED)) return true
        return false
    }
    return true
}

export interface ACLTestOptions {
    roles: Set<string>
    channel: string
    command: string
    category?: string
}

export default defineComponent({
    components: { InputSelect, ItemSelect, InputField },
    props: {
        rule: {
            type: Object as PropType<ACL>,
            default: () => ACL.empty(),
        },
        options: {
            type: Object as PropType<ACLRuleComponentOption>,
            default: () => ({}),
        },
    },
    emits: ['update:data'],
    setup() {
        return {
            modifiers: aclModifiers,
            actions: aclActions,
            ...setupDiscordModel(
                undefined,
                (c) =>
                    c.type == ChannelEnum.text || c.type == ChannelEnum.category
            ),
        }
    },
    data() {
        let name = this.rule.name
        let error = this.rule.error
        let modifier = this.rule.modifier
        let action = this.rule.action
        let roles = [...this.rule.roles]
        let channels = [...this.rule.channels]
        let commands = [...this.rule.commands]
        return {
            data: {
                name,
                error,
                modifier,
                action,
                roles,
                channels,
                commands,
                deleted: false,
            },
            _collapsed: false,
        }
    },
    computed: {
        slug(): string {
            return slugify(this.data.name).replace(' ', '-')
        },
        specificity(): string {
            let specificity = aclSpecificity(this.data)
            return `(${specificity.join(', ')})`
        },
        channelSelectors: {
            get(): string[] {
                return this.data.channels.map((k) =>
                    k in this.channels ? k : `deleted channel ${k}`
                )
            },
            set(v: string[]) {
                this.data.channels = v
            },
        },
        roleSelectors: {
            get(): string[] {
                return this.data.roles.map((k) =>
                    k in this.roles ? k : `deleted role ${k}`
                )
            },
            set(v: string[]) {
                this.data.roles = v
            },
        },
        commandSelectors: {
            get(): string[] {
                return this.data.commands.map((k) =>
                    k in this.commands ? k : `deleted command ${k}`
                )
            },
            set(v: string[]) {
                this.data.commands = v
            },
        },
        itemState(): {
            button: string
            buttonStyle: string[]
            headerStyle: string[]
            ruleLabel: string
            containerStyle: string[]
        } {
            if (this.data.deleted) {
                return {
                    containerStyle: ['form', 'disabled'],
                    button: 'Undelete rule',
                    buttonStyle: ['btn-delete', 'btn', 'btn-outline-info'],
                    headerStyle: ['acl-header', 'acl-deleted'],
                    ruleLabel: '(Deleted) Rule',
                }
            } else {
                return {
                    containerStyle: ['form'],
                    button: 'Delete rule',
                    buttonStyle: ['btn-delete', 'btn', 'btn-outline-danger'],
                    headerStyle: ['acl-header'],
                    ruleLabel: 'Rule',
                }
            }
        },
        deleteButton(): string[] {
            return this.data.deleted
                ? ['btn', 'btn-outline-info']
                : ['btn', 'btn-outline-danger']
        },
    },
    methods: {
        toggleDelete() {
            this.data.deleted = !this.data.deleted
        },
    },
    watch: {
        data: {
            handler(v: Pick<ACL, keyof ACL>) {
                this.$emit('update:data', v)
            },
            deep: true,
        },
    },
})
