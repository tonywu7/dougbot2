<template>
    <li :class="`field field-${type}`">
        <label
            v-if="label"
            v-html="label"
            :for="id"
            :class="labelState"
        ></label>
        <input
            :class="inputElem"
            :id="id"
            :type="type"
            :name="name"
            v-model="data"
        />
    </li>
</template>

<style lang="scss" scoped>
@import '../../styles/colors';
@import '../../styles/typefaces';

.form-control {
    &[type='text'],
    &[type='number'] {
        background-color: #00000000;
        color: inherit;

        padding: 0.5rem 0 0.5rem;

        border-radius: 0;
        border: none;
        border-bottom: 2px solid $bw-grey-13;

        &:focus,
        &:active {
            box-shadow: none;
            border-color: var(--accent);
        }

        &::placeholder {
            font-size: 0.9rem;
            font-weight: 500;
            font-family: $ui-fonts;
        }
    }
}

.form-check-input {
    margin-top: 0;
}

.field {
    display: flex;
    flex-flow: column nowrap;

    margin-top: 12pt;
    margin-bottom: 12pt;

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

.field-label {
    text-transform: uppercase;
    letter-spacing: 0.3px;
    font-weight: 400;
    font-size: 0.8rem;

    &.modified {
        color: $yellow-300;
    }
}
</style>

<script lang="ts" src="./InputField.vue.ts"></script>
