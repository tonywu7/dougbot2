<template>
    <div :class="['acl-list-container', {'loading': loading}]">
        <div class="acl-list-actions">
            <button type="button" class="btn btn-success btn-new" @click="createRule">Create a new rule</button>
            <button type="button" class="btn btn-primary" @click="submit">Save changes</button>
        </div>
        <div class="acl-list">
            <transition-group name="list-move">
                <acl-rule v-for="(rule, index) in merged" :key="rule._id" :rule="rule" :data="rule"
                    @update:data="(item) => updateRule(item, index)">
                </acl-rule>
            </transition-group>
        </div>
    </div>
</template>
<script lang="ts" src="./ACLList.vue.ts"></script>
<style lang="scss" scoped>
    .acl-list-container {
        display: flex;
        flex-flow: column nowrap;

        > :not(:first-child) {
            margin-block-start: 1rem;
        }
    }

    .acl-list {
        display: flex;
        flex-direction: column-reverse;

        > :not(:first-child) {
            margin-block-end: 1rem;
        }
    }

    .acl-list-actions {
        display: flex;
        flex-flow: row wrap;
        gap: .5rem;

        .btn-new {
            flex: 1 0 auto;
        }
    }
</style>