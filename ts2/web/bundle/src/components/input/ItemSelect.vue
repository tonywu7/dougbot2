<template>
    <div ref="container" class="item-select dropdown" @click="regenIndex">
        <label v-if="label" v-html="label" class="field-label"></label>
        <span ref="dropdown" class="item-select-field" data-bs-toggle="dropdown" data-bs-auto-close="outside"
            aria-expanded="false" @click="(e) => e.stopImmediatePropagation()">
            <button v-for="item in selected" :key="item.id" type="button" class="selected-item item-select-item"
                :style="styles(item, true)" v-html="item.content" @click="(e) => deselect(e, item)"></button>
            <input ref="searchBox" type="text" class="item-select-search" :placeholder="placeholder" v-model="search"
                @click="showDropdown" @focus="showDropdown" @blur="hideDropdown" @input="clearValidity">
        </span>
        <div v-if="$slots.hint" class="field-after field-hint">
            <slot name="hint">
                <p>{{ hint }}</p>
            </slot>
        </div>
        <ul class="dropdown-menu dropdown-menu-end">
            <li v-for="item in candidates" :key="item.id">
                <button type="button" :style="styles(item, false)" class="dropdown-item item-select-item"
                    v-html="item.content" @click="(e) => select(e, item)"></button>
            </li>
        </ul>
    </div>
</template>
<script lang="ts" src="./ItemSelect.vue.ts"></script>
<style lang="scss" scoped>
    @use "sass:color";
    @import '../../styles/colors';

    $hairline-color: color.scale($color-text, $alpha: -75%);

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
        padding: 6px;

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

        line-height: 1.5;
        padding: 0;
        margin: 0 0 0 .5rem;
        width: 40%;
        min-width: 270px;

        border: none;

        background-color: transparent;
        color: $color-text;

        text-overflow: ellipsis;

        &:focus-visible {
            outline: none;
        }
    }

    .dropdown-menu {
        width: 100%;
        max-height: 50vh;
        padding: 6pt;
        overflow-y: scroll;
        z-index: 2000;
    }

    .dropdown-item {
        padding: 4pt 8pt;
        margin: 0;
        border-radius: 0.25rem;

        font-weight: 600;
        font-size: 0.9rem;
        letter-spacing: -0.5px;

        &:hover,
        &:focus {
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