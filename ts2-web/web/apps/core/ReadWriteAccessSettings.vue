<template>
    <div :class="['logging-config-main', {loading: loading}]">
        <form-container>
            <template v-slot:form-fields>
                <div>
                    <p class="interactive-text">Grant a member <strong class="emphasis read">read</strong>
                        access to bot settings if they have <strong class="emphasis">any of</strong> the following
                        roles:
                    </p>
                    <item-select :items="roles" v-model:choices="readable"></item-select>
                </div>
                <div>
                    <p class="interactive-text">Grant a member <strong class="emphasis read-write">read
                            &amp; write</strong> access to bot settings if they have <strong class="emphasis">any
                            of</strong>
                        the following roles:</p>
                    <item-select :items="roles" v-model:choices="writable">
                        <template v-slot:hint>
                            <p>Members with the <strong>Manage Server</strong> permission will always have <strong>read
                                    &amp; write</strong> access to the control panel.</p>
                        </template>
                    </item-select>
                </div>
            </template>
            <template v-slot:form-after>
                <button type="button" :class="['btn btn-primary', buttonState]" @click="submit">Save</button>
            </template>
        </form-container>
    </div>
</template>
<script lang="ts" src="./ReadWriteAccessSettings.vue.ts"></script>
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