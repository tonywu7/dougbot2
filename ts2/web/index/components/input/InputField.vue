<template>
    <div :class="[containerType]">
        <label v-if="label" :for="id" :class="labelState" v-html="label"></label>
        <template v-if="type === 'textarea'">
            <textarea :class="inputElem" :id="id" :name="name" :placeholder="placeholder" :required="options.required"
                :autocomplete="options.autocomplete" v-model="value"></textarea>
        </template>
        <template v-else>
            <input :class="inputElem" :id="id" :type="type" :name="name" :placeholder="placeholder"
                :required="options.required" :autocomplete="options.autocomplete" v-model="value" />
        </template>
        <div v-if="$slots.hint" class="field-after input-field-hint">
            <slot name="hint"></slot>
        </div>
        <div v-else-if="hint" class="field-after input-field-hint">
            <p>{{ hint }}</p>
        </div>
        <div v-if="error" class="field-after field-error">
            <p v-html="error"></p>
        </div>
    </div>
</template>

<style lang="scss" scoped>
    @import '../../styles/colors';
    @import '../../styles/typefaces';

    .form-control[type='text'],
    .form-control[type='number'],
    textarea.form-control {
        background-color: #00000000;
        color: inherit;

        padding: 0.5rem 0 0.5rem;

        border-radius: 0;
        border: none;
        border-bottom: 2px solid $bw-grey-13;

        &:focus,
        &:active {
            box-shadow: none;
            border-color: $color-accent;
        }

        &::placeholder {
            font-size: 0.9rem;
            font-weight: 500;
            font-family: $ui-fonts;
        }
    }

    .form-check-input {
        margin-top: 0;
        cursor: pointer;
    }

    .field {
        display: flex;
        flex-flow: column nowrap;

        &:first-child {
            margin-top: 0;
        }

        &:last-child {
            margin-bottom: 0;
        }

        &::marker {
            content: '';
            display: none;
        }
    }

    .field-checkbox,
    .field-radio {
        flex-flow: row-reverse nowrap;
        align-items: center;
        justify-content: flex-end;

        input {
            margin-inline-end: 6pt;
        }
    }
</style>

<script lang="ts" src="./InputField.vue.ts"></script>