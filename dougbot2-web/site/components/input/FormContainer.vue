<template>
    <form class="form" :method="method" :action="action">
        <div v-if="$slots['form-before']" class="form-before">
            <slot name="form-before"></slot>
        </div>
        <div class="form-fields">
            <slot name="form-fields"></slot>
        </div>
        <div v-if="$slots['form-after']" class="form-after">
            <slot name="form-after"></slot>
        </div>
    </form>
</template>
<script lang="ts" src="./FormContainer.vue.ts"></script>