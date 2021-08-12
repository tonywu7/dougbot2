<template>
    <div :class="['timezone-list-container', {'loading': loading}]">
        <div class="timezone-list">
            <transition-group name="fade">
                <form-container v-for="(tz, index) in data" :key="tz">
                    <template v-slot:form-fields>
                        <item-select label="Role" if-no-result="No matching role." :items="roles"
                            v-model:choices="tz.roles" @update:choices="() => updateClockAt(index)">
                        </item-select>
                        <item-select label="Timezone" if-no-result="No matching timezone." :items="zones"
                            v-model:choices="tz.zones" :options="{multiple: false}"
                            @update:choices="() => updateClockAt(index)">
                        </item-select>
                        <div class="clock">
                            <span class="local-time" v-html="clocks[index].time"></span>
                            <span class="field-label timezone-name" v-html="clocks[index].zone"></span>
                        </div>
                    </template>
                </form-container>
            </transition-group>
        </div>
        <div class="timezone-list-actions">
            <button type="button" class="btn btn-success btn-new" @click="createTimezone">Set timezone for a new
                role</button>
            <button type="button" class="btn btn-primary" @click="submit">Save changes</button>
        </div>
    </div>
</template>
<script lang="ts" src="./TimezoneList.vue.ts"></script>
<style lang="scss" scoped>
    @import '~/../ts2/web/index/styles/colors';

    .timezone-list-container {
        display: flex;
        flex-flow: column nowrap;
        gap: 1rem;
    }

    .timezone-list-actions {
        display: flex;
        flex-flow: row wrap;
        gap: .5rem;

        .btn-new {
            flex: 1 0 auto;
        }
    }

    .timezone-list {
        display: flex;
        flex-flow: column nowrap;
        gap: .5rem;
    }

    :deep(.form-fields) {
        display: grid;
        grid-template-columns: minmax(0, 3fr) minmax(0, 3fr) minmax(0, 2fr);
        align-items: center;

        >* {
            justify-self: stretch;
        }

        @media screen and (max-width: $display-width-small) {
            grid-template-columns: 1fr;
        }
    }

    .clock {
        display: flex;
        flex-flow: column nowrap;
        gap: .25rem;
        justify-content: center;
        align-items: center;

        @media screen and (max-width: $display-width-small) {
            flex-flow: row-reverse;
            justify-content: space-between;
        }
    }

    .local-time {
        font-weight: 300;
        font-size: 1.4rem;

        @media screen and (max-width: $display-width-small) {
            font-size: 1.2rem;
        }
    }

    .timezone-name {
        line-height: 1.5;
        text-align: center;
    }
</style>