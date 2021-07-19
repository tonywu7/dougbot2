<template>
    <form class="form">
        <slot name="form-before"></slot>
        <ul class="form-fields">
            <slot name="form-fields"></slot>
        </ul>
        <slot name="form-after"></slot>
    </form>
</template>

<script lang="ts" src="./FormContainer.vue.ts"></script>