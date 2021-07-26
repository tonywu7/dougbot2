<template>
    <div :class="['logging-config-main', {loading: loading}]">
        <form-container>
            <template v-slot:form-fields>
                <div>
                    <p class="interactive-text">Grant a member <strong class="emphasis read">read</strong> access to bot
                        settings if they have <strong class="emphasis">all of</strong> the following permissions:</p>
                    <item-select :items="permissions" v-model:choices="readable">
                    </item-select>
                </div>
                <div>
                    <p class="interactive-text">Grant a member <strong class="emphasis read-write">read and
                            write</strong> access to bot settings if they have <strong class="emphasis">all of</strong>
                        the following permissions:</p>
                    <item-select :items="permissions" v-model:choices="writable">
                    </item-select>
                </div>
            </template>
            <template v-slot:form-after>
                <button type="button" :class="['btn btn-primary', buttonState]" @click="submit">Save</button>
            </template>
        </form-container>
    </div>
</template>
<script lang="ts" src="./PermissionSettings.vue.ts"></script>
<style lang="scss">
    @import "../../styles/colors";

    .emphasis {
        text-decoration: underline;
    }

    .read {
        color: $blue;
    }

    .read-write {
        color: $yellow;
    }

    .form-fields {
        margin: 0 0 .5rem 0;
    }

    .form-after {
        display: flex;
        flex-flow: column nowrap;
    }
</style>