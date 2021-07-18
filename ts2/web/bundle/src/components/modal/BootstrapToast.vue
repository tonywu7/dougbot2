<template>
    <teleport to="#toast-container">
        <div ref="main" :class="['toast align-items-center border-0', header ? [] : theming]" role="alert"
            aria-live="{{ ariaLive }}" aria-atomic="true">
            <div :class="['d-flex', header ? 'flex-column' : 'flex-row']">
                <template v-if="header">
                    <div :class="['toast-header', theming]">
                        <b v-html="header"></b>
                        <button type="button" :class="['btn-close', btnColor]" data-bs-dismiss="toast"
                            aria-label="Close"></button>
                    </div>
                    <div v-html="message" class="toast-body text-dark"></div>
                </template>
                <template v-else>
                    <div class="toast-body">
                        <b v-html="message"></b>
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"
                        aria-label="Close"></button>
                </template>
            </div>
        </div>
    </teleport>
</template>
<script lang="ts" src="./BootstrapToast.vue.ts"></script>
<style lang="scss" scoped>
    :deep(*) {
        .errorlist {
            color: inherit;
        }

        .toast-header {
            justify-content: space-between;

            b {
                letter-spacing: -.2px;
            }
        }

        ul {
            margin: .3rem 0;
            padding: 0;
        }

        li {
            display: block;
        }
    }
</style>