<template>
    <div ref="container" class="item-select dropdown">
        <label v-if="label" v-html="label" class="field-label"></label>
        <div ref="searchElem" class="item-select-field" aria-expanded="false" @click="activate" @focusin="activate"
            @focusout="deactivate">
            <button v-for="item in selected" :key="item.id" type="button" tabindex="-1" class="selected-item"
                :style="getItemStyles(item, true)" v-html="item.content" @click="(e) => deselect(item)"></button>
            <textarea ref="searchInput" type="search" class="item-select-search" wrap="off" autocomplete="off"
                autocapitalize="none" spellcheck="false" :style="[inputWidth]" :value="search" @click="showDropdown"
                @input="updateSearch" @keydown="navigateList"></textarea>
            <ul ref="candidateList" role="listbox" aria-multiselectable="true" :aria-expanded="dropdownShow"
                :aria-hidden="!dropdownShow" :class="['dropdown-menu', {show: dropdownShow}]">
                <li v-for="(item, index) in candidates" :key="item.id" role="button"
                    :class="['dropdown-item', {'has-focus': index == currentFocus}]" :style="getItemStyles(item, false)"
                    :aria-selected="index == currentFocus" v-html="item.content" @click="(e) => select(item)"
                    @mouseenter="currentFocus = index">
                </li>
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

    $hairline-color: color.scale($color-text, $alpha: -75%);
    $field-padding: 6px;

    .item-select {
        display: flex;
        flex-flow: column nowrap;
    }

    .item-select-field {
        display: inline;
        line-height: 1.8;

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
    }

    .field-hint {
        margin: .25rem 0 0;
    }

    .selected-item {
        display: inline-block;

        margin: 0 1.8px;
        padding: 0.25em .3rem;
        border-radius: 0.25em;
        border: none;

        line-height: 1;
        font-weight: 600;

        cursor: pointer;
        user-select: none;

        &:focus-visible {
            outline: none;
        }
    }

    .item-select-search {
        display: inline-block;

        line-height: 1;
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

    .dropdown-menu {
        width: 100%;
        max-height: 40vh;
        padding: 6pt;
        overflow-y: scroll;
        z-index: 2000;
        top: 100%;
        left: 0;
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
            background-color: $bw-grey-6;
        }

        &:active {
            background-color: $bw-grey-7;
            color: $bw-grey-14;
            box-shadow: var(--box-shadow-focus-bright);
        }

        cursor: pointer;

        &.hidden {
            display: none;
        }
    }

    .dropdown-toggle::after {
        display: none;
    }
</style>