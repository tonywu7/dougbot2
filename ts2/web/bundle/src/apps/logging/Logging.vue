<template>
    <div :class="['logging-config-main', {loading: loading}]">
        <div class="logging-conf">
            <form-container v-for="cls in conf" :class="{'superuser': cls.superuser}" :key="cls">
                <template v-slot:form-before>
                    <h4 class="logging-name" v-html="cls.name"></h4>
                </template>
                <template v-slot:form-fields>
                    <item-select label="Send logs to this channel" :items="textChannels"
                        v-model:choices="logging[cls.key].channels" placeholder="type in the name of a channel"
                        :options="{multiple: false}">
                    </item-select>
                    <item-select label="Notify this role for every log message" :items="roles"
                        v-model:choices="logging[cls.key].roles" placeholder="type in the name of a role"
                        :options="{multiple: false}">
                    </item-select>
                </template>
            </form-container>
        </div>
        <button type="button" class="btn btn-success btn-submit" @click="submit">Save settings</button>
    </div>
</template>
<script lang="ts" src="./Logging.vue.ts"></script>
<style lang="scss" scoped>
    @import '../../styles/colors';

    .logging-config-main {
        display: flex;
        flex-flow: column nowrap;
        gap: 1rem;
        justify-content: space-between;
    }

    .logging-conf {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.2rem 1.2rem;

        @media screen and (max-width: 1152px) {
            grid-template-columns: 1fr;
        }

        @media screen and (min-width: 768px) and (max-width: 1152px) {
            grid-template-columns: 1fr 1fr;
        }

        @media screen and (max-width: 768px) {
            grid-template-columns: 1fr;
        }
    }

    .logging-name {
        margin: 0 0 1rem;
    }

    .superuser {

        .logging-name,
        :deep(.field-label) {
            color: $yellow;
        }
    }

    .btn-success {
        height: 2.5rem;
        font-weight: 700;
    }
</style>