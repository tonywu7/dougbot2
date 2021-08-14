<template>
    <form-container>
        <template v-slot:form-fields>
            <input-field v-for="ext in extensions" :key="ext.id" :id="`extension-toggle-${ext.id}`" type="checkbox"
                :name="ext.id" :label="ext.label" :options="{useSwitch: true}" v-model:value="values[ext.id]">
            </input-field>
        </template>
        <template v-slot:form-after>
            <button type="button" :class="['btn btn-primary', processing ? 'disabled' : '']" @click="submit">
                Save
            </button>
        </template>
    </form-container>
</template>

<script lang="ts" src="./ExtensionSettings.vue.ts"></script>

<style lang="scss" scoped>
    @import "../../styles/colors";

    :deep(.form-fields) {
        padding: 1rem;

        display: flex;
        flex-flow: row wrap;
        column-gap: 6pt;
        row-gap: 6pt;

        .field {
            margin: 0;
            flex: 1 1 45%;

            @media screen and (max-width: $display-width-small) {
                flex: 1 0 100%;
            }
        }

        .field-label {
            text-transform: none;
            font-size: 1.1rem;
            font-weight: 600;
            letter-spacing: -0.5px;
            user-select: none;
        }

        i.bi::before {
            position: relative;
            top: 0px;
            font-size: 0.9em;
            margin-right: 4px;
        }

        .form-check-input {
            background-color: $red;
            border-color: $red;

            &:focus {
                background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='rgba%280, 0, 0, 0.25%29'/%3e%3c/svg%3e");
            }

            &:checked {
                background-color: $green-400;
                border-color: $green-400;
            }

            &:focus:checked {
                background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%23fff'/%3e%3c/svg%3e");
            }
        }
    }

    :deep(.form-after) {
        display: flex;
        flex-flow: column nowrap;
        margin: 0;
    }
</style>