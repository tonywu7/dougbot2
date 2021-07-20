<template>
    <div class="form">
        <h4>Test out access control settings:</h4>
        <div>
            <item-select label="Member with roles" :items="roles" v-model:choices="selected.roles"
                placeholder="type in the name of a role">
            </item-select>
            <item-select label="Using command" :items="commands" v-model:choices="selected.command"
                placeholder="type in a command" :multiple="false">
            </item-select>
            <item-select label="In channel" :items="channels" v-model:choices="selected.channel"
                placeholder="type in the name of a channel" :multiple="false"></item-select>
            <div class="test">
                <button type="button" class="btn btn-outline-primary btn-submit">Test</button>
                <h4 class="test-result" v-html="result"></h4>
            </div>
        </div>
    </div>
</template>
<script lang="ts" src="./ACLInspect.vue.ts"></script>
<style lang="scss" scoped>
    .item-select {
        margin: .5rem 0;
    }

    .test {
        display: flex;
        flex-flow: row nowrap;
        gap: .6rem;

        .btn {
            width: min-content;
            margin: 0;
        }

        .test-result {
            margin: 0;
        }
    }
</style>