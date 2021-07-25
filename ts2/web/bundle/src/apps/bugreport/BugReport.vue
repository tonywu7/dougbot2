<template>
    <form-container method="POST" :action="action">
        <template v-slot:form-fields>
            <csrf-token></csrf-token>
            <input-select label="What type of feedback" name="topic" :options="reportTypes" v-model:value="topic">
            </input-select>
            <template v-if="topic !== 0">
                <input-field type="textarea" name="summary" label="Description" :hint="summaryHint"
                    :options="{showChanged: false, required: true}" v-model:value="summary">
                </input-field>
                <input-field v-if="pathLabel" type="text" name="path" :label="pathLabel"
                    :options="{showChanged: false, autocomplete: 'off'}" v-model:value="path"></input-field>
            </template>
        </template>
        <template v-if="topic !== 0" v-slot:form-after>
            <button type="submit" class="btn btn-primary">Submit</button>
        </template>
    </form-container>
</template>
<script lang="ts" src="./BugReport.vue.ts"></script>
<style lang="scss" scoped>
    :deep(.form-after) {
        display: flex;
        flex-flow: column nowrap;
    }
</style>