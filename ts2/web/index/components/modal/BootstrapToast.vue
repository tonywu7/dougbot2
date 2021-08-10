<template>
    <teleport to="#toast-container">
        <div ref="main" :class="['toast align-items-center border-0', header ? [] : theming]" role="alert"
            aria-live="polite" aria-atomic="true">
            <div :class="['d-flex position-relative', header ? 'flex-column' : 'flex-row']">
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
                    <button type="button" :class="['btn-close me-2 m-auto', btnColor]" data-bs-dismiss="toast"
                        aria-label="Close"></button>
                </template>
            </div>
        </div>
    </teleport>
</template>
<script lang="ts" src="./BootstrapToast.vue.ts"></script>
<style lang="scss" scoped>
    @import '../../styles/colors';

    :deep(*) {
        .toast {
            @media screen and (max-width: $display-width-small) {
                background-color: $gray-200;
            }
        }

        .errorlist {
            color: inherit;
        }

        .toast-header {
            font-size: 1rem;

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

        .btn-close {
            padding: 1px 6px;
        }
    }
</style>