<template>
    <form class="form">
        <slot name="form-before"></slot>
        <div class="form-fields">
            <slot name="form-fields"></slot>
        </div>
        <slot name="form-after"></slot>
    </form>
</template>

<script lang="ts" src="./FormContainer.vue.ts"></script>