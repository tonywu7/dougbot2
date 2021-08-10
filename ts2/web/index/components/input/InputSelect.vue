<template>
    <div class="flex-select-container">
        <label v-if="label" :for="id" class="field-label" v-html="label"></label>
        <div class="flex-select">
            <span class="actionable" v-html="display"></span>
            <select :id="id" class="flex-select-input" :name="name" v-model="_value">
                <option v-for="opt in options" :key="opt" :value="opt.value">{{ opt.text }}</option>
            </select>
        </div>
    </div>
</template>
<script lang="ts" src="./InputSelect.vue.ts"></script>
<style lang="scss" scoped>
    @import '../../styles/colors';

    .flex-select-container {
        display: flex;
        flex-flow: row nowrap;
        align-content: center;
        align-items: baseline;
    }

    .field-label {
        margin: 0 .5rem 0 0;

        &::after {
            content: ":";
        }
    }

    .flex-select {
        display: block;
        position: relative;
        overflow-x: hidden;

        &:focus-within {
            box-shadow: $box-shadow-focus;
        }

        >.actionable {
            pointer-events: none;
            font-weight: 700;
            font-size: 1rem;
            text-decoration: 1px dotted underline;
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