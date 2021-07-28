<template>
    <div :class="itemState.containerStyle">
        <header :class="itemState.headerStyle">
            <input-field :id="slug" type="text" name="name" :label="itemState.ruleLabel" :options="{showChanged: false}"
                :validator="options.nameValidator" v-model:value="data.name">
            </input-field>
            <button class="btn btn-collapse" :class="[_collapsed ? '' : 'show']" @click="_collapsed = !_collapsed"><i
                    class="bi bi-chevron-down"></i></button>
        </header>
        <transition name="fade">
            <div class="acl-body" v-show="!_collapsed">
                <div class="acl-details">
                    <item-select label="Where" :items="channels" v-model:choices="channelSelectors">
                        <template v-slot:hint>
                            <p>Leave blank to apply to all channels</p>
                        </template>
                    </item-select>
                    <item-select label="What" :items="commands" v-model:choices="commandSelectors">
                        <template v-slot:hint>
                            <p>Leave blank to apply to all commands</p>
                        </template>
                    </item-select>
                    <div class="acl-roles">
                        <input-select label="Who" :options="modifiers" v-model:value="data.modifier">
                        </input-select>
                        <item-select :items="roles" v-model:choices="roleSelectors">
                            <template v-slot:hint>
                                <p>Leave blank to apply to all everyone</p>
                            </template>
                        </item-select>
                    </div>
                    <div class="acl-action">
                        <input-select label="How" :options="actions" v-model:value="data.action"></input-select>
                    </div>
                </div>
                <div class="acl-extra">
                    <div class="field">
                        <label class="field-label">Specificity (calculated)</label>
                        <p class=acl-specificity v-html="specificity"></p>
                    </div>
                    <input-field type="textarea" name="Error message" :options="{showChanged: false}"
                        v-model:value="data.error">
                        <template v-slot:hint>
                            <p>Message to show when a member fails this rule</p>
                        </template>
                    </input-field>
                    <button type="button" :class="itemState.buttonStyle" v-html="itemState.button"
                        @click="toggleDelete"></button>
                </div>
            </div>
        </transition>
    </div>
</template>
<script lang="ts" src="./ACLRule.vue.ts"></script>
<style lang="scss" scoped>
    @import '../../styles/colors';
    @import '../../styles/typefaces';

    .acl-body {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1.5rem;

        margin-top: 1rem;

        @media screen and (max-width: $display-width-small) {
            display: flex;
            flex-flow: column nowrap;
            gap: 1rem;
        }
    }

    .acl-details,
    .acl-extra {
        display: flex;
        flex-flow: column nowrap;
    }

    .acl-details {
        gap: .5rem;
    }

    .acl-header {
        color: $yellow-500;
        position: relative;

        margin: 0;

        .field {
            margin: 0;
        }

        :deep(.form-control[type='text']) {
            font-size: 1.4rem;
            font-weight: 300;
            letter-spacing: -0.3px;
            color: $yellow-500;
            border-color: $yellow-500;
        }

        :deep(.field-label) {
            color: $yellow-500;
        }

    }

    .acl-header.acl-deleted {
        color: $red;

        :deep(.form-control[type='text']) {
            color: $red;
            border-color: $red;
            text-decoration: solid line-through 1px;
        }

        :deep(.field-label) {
            color: $red;
        }
    }

    .acl-roles {
        display: flex;
        flex-flow: column nowrap;

        .flex-select-container {
            flex: 0 0 auto;

            &[value="NONE"] :deep(.actionable) {
                color: $orange-400;
            }

            &[value="ANY"] :deep(.actionable) {
                color: $teal-400;
            }

            &[value="ALL"] :deep(.actionable) {
                color: $indigo-400;
            }
        }

        .item-select {
            flex: 1 1 auto;
        }
    }

    :deep(.item-select-field) {
        margin: 0;
    }

    .acl-action {
        .flex-select-container {
            &[value="DISABLED"] :deep(.actionable) {
                color: $red;
            }

            &[value="ENABLED"] :deep(.actionable) {
                color: $cyan;
            }
        }
    }

    .acl-specificity {
        font-size: 1.5rem;
        font-weight: 600;
    }

    .btn-delete {
        margin: 1rem 0 0 0;
        align-self: flex-start;
    }

    :deep(.field-label) {
        line-height: 24px;
    }

    .form.disabled {

        .acl-details,
        .acl-extra .field {
            pointer-events: none;
            filter: opacity(.5);
        }

        .acl-header .field {
            pointer-events: none;
        }
    }

    .btn-collapse {
        position: absolute;
        top: 0;
        right: 0;
        margin: 0;

        font-size: 1.5rem;
        color: inherit;

        transition: transform .3s ease;

        &.show {
            transform: rotate(180deg);
        }
    }

    .fade-enter-active,
    .fade-leave-active {
        transition: opacity 0.3s ease;
    }

    .fade-enter-from,
    .fade-leave-to {
        opacity: 0;
    }
</style>