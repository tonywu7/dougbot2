<template>
    <div ref="container" class="item-select dropdown">
        <template v-if="$slots.label">
            <label class="field-label">
                <slot name="label"></slot>
            </label>
        </template>
        <label v-else-if="label" v-html="label" class="field-label"></label>
        <div ref="searchElem" :class="['item-select-field', overflowDirection]" :aria-expanded="dropdownShow"
            @click="activate" @focus="activate" @blur="deactivate">
            <button v-for="item in selected" :key="item.id" type="button" tabindex="-1" class="selected-item"
                :style="getItemStyles(item, true)" v-html="safe(item.content)" @click="(e) => deselect(item, e)"
                @focusin="(e) => e.stopPropagation()"></button>
            <textarea ref="searchInput" type="search" class="item-select-search" wrap="off" autocomplete="off"
                autocapitalize="none" spellcheck="false" :style="[inputWidth]" :value="search" @focus="activate"
                @blur="deactivate" @input="updateSearch" @keydown="navigateList"></textarea>
            <ul v-if="dropdownShow" ref="candidateList" role="listbox" aria-multiselectable="true"
                :aria-expanded="dropdownShow" :aria-hidden="!dropdownShow"
                :class="['dropdown-menu', {show: dropdownShow}]">
                <li v-for="(item, index) in candidates" :key="item.id" role="button"
                    :class="['dropdown-item', {'has-focus': index == currentFocus}]" :style="getItemStyles(item, false)"
                    :aria-selected="index == currentFocus" v-html="safe(item.content)" @click="(e) => select(item)"
                    @touchmove.passive="() => dragging = true" @touchend="(e) => handleTouch(item, e)"
                    @mouseenter="currentFocus = index">
                </li>
                <span class="empty-message" v-if="ifNoResult" v-html="ifNoResult"></span>
            </ul>
        </div>
        <div v-if="$slots.hint" class="field-after field-hint">
            <slot name="hint"></slot>
        </div>
    </div>
</template>
<script lang="ts" src="./ItemSelect.vue.ts"></script>
<style lang="scss" scoped>
    @use "sass:color";
    @import '../../styles/colors';

    $field-padding: 6px;

    .item-select {
        display: flex;
        flex-flow: column nowrap;
    }

    .item-select-field {
        position: relative;

        display: inline-flex;
        flex-flow: row wrap;
        align-items: center;

        line-height: 1.8;
        min-height: 2.5rem;

        font-size: 0.9rem;
        color: $color-text;
        border: 1px solid $hairline-color;

        border-radius: 4px;
        margin: .5rem 0 0;
        padding: $field-padding;

        cursor: text;

        >* {
            margin: 0;
        }

        &[aria-expanded="true"] {
            box-shadow: 0 0 4px 4px color.change($color-accent, $alpha: .08), 0 0 8px 8px color.change($color-accent, $alpha: .05);

            .dropdown-menu {
                box-shadow: 0 0 4px 4px rgba(0, 0, 0, 0.12), 0 0 8px 8px rgba(0, 0, 0, 0.09);
            }

            &.normal {
                border-bottom-left-radius: 0;
                border-bottom-right-radius: 0;

                .dropdown-menu {
                    top: calc(100% + 1px);
                    border-top-left-radius: 0;
                    border-top-right-radius: 0;
                    border-top-width: 0;
                }
            }

            &.flipped {
                border-top-left-radius: 0;
                border-top-right-radius: 0;

                .dropdown-menu {
                    bottom: calc(100% + 1px);
                    border-bottom-left-radius: 0;
                    border-bottom-right-radius: 0;
                    border-bottom-width: 0;
                }
            }
        }
    }

    .item-select-search {
        display: inline-block;

        line-height: 1.2;
        padding: 0;
        margin: 0 0 0 .5rem;

        height: 1.2em;
        min-width: 20px;
        max-width: calc(100% - (#{$field-padding * 2}));
        vertical-align: middle;

        resize: none;
        border: none;

        background-color: transparent;
        color: $color-text;

        overflow: hidden;
        overflow-wrap: break-word;

        &:focus {
            box-shadow: none;
        }

        &:focus-visible {
            outline: none;
        }
    }

    .selected-item {
        display: inline-flex;
        align-items: center;

        margin: 2.2px 1.8px;
        padding: 0.25em .3rem;
        border-radius: 0.25em;
        border: none;

        line-height: 1;
        font-weight: 600;

        overflow: hidden;
        text-overflow: ellipsis;
        max-width: calc(100% - 3.6px);
        max-height: 1.5em;

        cursor: pointer;
        user-select: none;

        &:focus-visible {
            outline: none;
        }
    }

    .dropdown-menu {
        width: calc(100% + 2px);
        max-height: 40vh;
        padding: 6pt;
        overflow-y: scroll;
        z-index: 2000;
        left: -1px;
        background-color: $bw-grey-3;
        border: 1px solid $hairline-color;
    }

    .dropdown-item {
        padding: 4pt 8pt;
        margin: 0;
        border-radius: 0.25rem;

        font-weight: 600;
        font-size: 0.9rem;
        letter-spacing: -0.4px;
        line-height: 1.5;

        white-space: normal;

        &:hover,
        &:focus {
            background-color: unset;
        }

        &.has-focus {
            background-color: $bw-grey-5;
        }

        &:active {
            background-color: $bw-grey-6;
            color: $bw-grey-14;
            box-shadow: $box-shadow-focus-bright;
        }

        cursor: pointer;

        &.hidden {
            display: none;
        }
    }

    .dropdown-toggle::after {
        display: none;
    }

    .field-hint {
        margin: .25rem 0 0;
    }

    .empty-message {
        display: none;

        color: $bw-grey-9;
        font-size: .8rem;
        text-align: center;

        &:first-child {
            display: block;
        }
    }
</style>