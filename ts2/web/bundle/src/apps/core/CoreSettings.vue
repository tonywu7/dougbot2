<template>
    <form-container>
        <template v-slot:form-fields>
            <input-field ref="input" :id="'id-prefix'" :type="'text'" :name="'prefix'" :validator="validate"
                v-model:value="value" v-model:error="error">
                <template v-slot:hint>
                    <p>Example command: <code><span v-html="value"></span>echo</code></p>
                </template>
            </input-field>
        </template>
        <template v-slot:form-after>
            <button type="button" :class="['btn btn-primary', buttonState]" @click="submit">Save setting</button>
        </template>
    </form-container>
</template>

<script lang="ts" src="./CoreSettings.vue.ts"></script>

<style lang="scss" scoped>
    @import '../../styles/typefaces';

    :deep(#id-prefix) {
        font-family: $monospace-fonts;
        font-weight: 700;
        font-size: 1.2rem;
    }
</style>