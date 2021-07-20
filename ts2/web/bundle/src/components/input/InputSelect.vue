<template>
    <div class="flex-select">
        <span class="actionable" v-html="display"></span>
        <select class="flex-select-input" v-model="_value">
            <option v-for="opt in options" :key="opt" :value="opt.value">{{ opt.text }}</option>
        </select>
    </div>
</template>
<script lang="ts" src="./InputSelect.vue.ts"></script>
<style lang="scss" scoped>
    .flex-select {
        display: block;
        position: relative;
        overflow-x: hidden;

        &:focus-within {
            box-shadow: var(--box-shadow-focus);
        }

        >.actionable {
            pointer-events: none;
        }

        >.flex-select-input {
            position: absolute;
            cursor: pointer;
            left: 0;
            top: 0;
            bottom: 0;
            opacity: 0;
            padding: 0;
            margin: 0;
        }
    }
</style>