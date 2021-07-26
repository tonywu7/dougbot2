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
                <p v-if="pathLabel" class="interactive-text">If you know what you are doing, you should file an issue on
                    the <a href="/github">GitHub repo</a> instead.</p>
            </template>
        </template>
        <template v-if="topic !== 0" v-slot:form-after>
            <button type="submit" class="btn btn-primary">Submit</button>
        </template>
    </form-container>
</template>
<script lang="ts" src="./BugReport.vue.ts"></script>
<style lang="scss" scoped>
    @import "../../styles/typefaces";

    :deep(.form-after) {
        display: flex;
        flex-flow: column nowrap;
    }

    .article-view .main-content p {
        font-family: $ui-fonts;
    }

    :deep(.field-after) {
        p {
            font-family: $ui-fonts;
            font-size: .8rem;
            font-weight: 400;
            margin: 0;
        }
    }
</style>