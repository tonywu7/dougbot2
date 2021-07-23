<template>
    <div class="acl-list-container">
        <div class="acl-list-actions">
            <button type="button" class="btn btn-success btn-new" @click="createRule">Create a new rule</button>
            <button type="button" class="btn btn-primary" @click="submit">Save changes</button>
        </div>
        <div class="acl-list">
            <transition-group name="list-move">
                <acl-rule v-for="(rule, index) in merged" :key="index" :rule="rule" :data="merged[index]"
                    @update:data="(item) => updateRule(item, index)">
                </acl-rule>
            </transition-group>
        </div>
    </div>
</template>
<script lang="ts" src="./ACLList.vue.ts"></script>
<style lang="scss" scoped>
    .acl-list-container,
    .acl-list {
        display: flex;
        flex-flow: column nowrap;
        gap: 1rem;
    }

    .acl-list {
        flex-direction: column-reverse;
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