<template>
    <div>
        <teleport to="#acl-inspect">
            <acl-inspect :state="inspectorState" @run-test="runInspector" @clear="clearInspector"></acl-inspect>
        </teleport>
        <teleport to="#acl-list">
            <acl-list ref="rulesApp" @update:data="() => inspectorState = undefined"></acl-list>
        </teleport>
    </div>
</template>
<script lang="ts" src="./App.vue.ts"></script>