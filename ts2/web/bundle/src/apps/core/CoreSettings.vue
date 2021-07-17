<template>
    <div>
        <input-field
            id="id-1"
            type="text"
            name="prefix"
            :initial="original"
            v-model:data="value"
        ></input-field>
        <p>
            Example command: <code><span v-html="prefix"></span>echo</code>
        </p>
    </div>
</template>

<script lang="ts" src="./CoreSettings.vue.ts"></script>
