<template>
    <form-container>
        <template v-slot:form-fields>
            <input-field
                ref="input"
                :id="'id-prefix'"
                :type="'text'"
                :name="'prefix'"
                v-model:value="value"
            >
                <template v-slot:hint>
                    <p>Example command: <code><span v-html="value"></span>echo</code></p>
                </template>
            </input-field>
        </template>
    </form-container>
</template>

<script lang="ts" src="./CoreSettings.vue.ts"></script>

<style lang="scss" scoped>
@import '../../styles/typefaces';

:deep(#id-prefix) {
    font-family: $ui-fonts;
    font-weight: 700;
    font-size: 1.2rem;
}
</style>
