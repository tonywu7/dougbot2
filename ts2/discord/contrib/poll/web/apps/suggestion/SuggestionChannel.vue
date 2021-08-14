<template>
    <div :class="{loading: loading}">
        <div>
            <ul class="suggestion-channel-tabs">
                <li class="tab" v-for="(ch, idx) in data" :key="ch" :class="{active: ch === current}">
                    <button type="button" class="btn" :disabled="willDelete" v-html="display(idx)"
                        @click="activate(idx)"></button>
                </li>
                <li class="tab">
                    <button type="button" class="btn" :disabled="willDelete" @click="createChannel"><i
                            class="bi bi-plus-lg"></i></button>
                </li>
            </ul>
        </div>

        <div class="suggestion-channel-body">

            <form-container v-if="current">
                <template v-slot:form-fields>

                    <div class="suggestion-channel">
                        <item-select class="suggestion-channel-select" label="Channel" :items="channels"
                            :multiple="false" :filter="channelFilter" v-model:choices="current.channel"
                            v-model:error="error">
                        </item-select>
                    </div>

                    <transition name="fade">
                        <div :class="['suggestion-channel-options', {disabled: disabled}]">

                            <div class="form-fields miscellaneous-options">
                                <input-field type="text" name="title" :id="`suggest-channel-title`"
                                    v-model:value="current.title">
                                    <template v-slot:hint>
                                        <p>Used as the message title for all submissions in this channel.
                                        </p>
                                    </template>
                                </input-field>
                                <input-field type="textarea" name="description" :id="`suggest-channel-description`"
                                    v-model:value="current.description">
                                    <template v-slot:hint>
                                        <p>Shown as help text when people use the suggest command to see a list of all
                                            suggestion channels.</p>
                                    </template>
                                </input-field>
                                <input-field type="checkbox" name="requiresText" label="Suggestion requires text"
                                    :id="`suggest-channel-requires-text`" v-model:value="current.requiresText">
                                </input-field>
                                <input-field type="number" name="requiresUploads" label="Minimum # of files"
                                    :id="`suggest-channel-requires-uploads`" v-model:value="current.requiresUploads">
                                </input-field>
                                <input-field type="number" name="requiresLinks" label="Minimum # of links"
                                    :id="`suggest-channel-requires-links`" v-model:value="current.requiresLinks">
                                </input-field>
                            </div>

                            <div class="form-fields">
                                <div class="emote-selection">
                                    <item-select label="Upvote" :items="emotes" :multiple="false" :unsafe="true"
                                        v-model:choices="current.upvote" :factory="emoteFactory">
                                    </item-select>
                                    <item-select label="Downvote" :items="emotes" :multiple="false" :unsafe="true"
                                        v-model:choices="current.downvote" :factory="emoteFactory">
                                    </item-select>
                                </div>
                                <item-select label="Arbiters" :items="roles" v-model:choices="current.arbiters">
                                    <template v-slot:hint>
                                        <p>Members with <u>any</u> of these roles can use the following reactions. They
                                            can also add comments to any suggestion.</p>
                                    </template>
                                </item-select>
                                <label class="field-label">Reactions</label>
                                <ul class="reaction-list">
                                    <li v-for="(r, index) in current._reactions" :key="r" class="reaction-row">
                                        <a class="text-danger" href="#" @click.prevent="removeReaction(index)">
                                            <i class="bi bi-dash-circle"></i></a>
                                        <span class="reaction-pair">
                                            <item-select :items="emotes" :multiple="false" :unsafe="true"
                                                v-model:choices="r.emote" :factory="emoteFactory">
                                            </item-select>
                                            <input-field type="text" v-model:value="r.message">
                                            </input-field>
                                        </span>
                                    </li>
                                    <li class="reaction-row">
                                        <a class="text-success" href="#" @click.prevent="addReaction()">
                                            <i class="bi bi-plus-circle"></i></a>
                                    </li>
                                </ul>
                            </div>

                        </div>
                    </transition>
                </template>

                <template v-slot:form-after>
                    <div class="suggestion-channel-actions">
                        <button v-if="!willDelete" type="button" class="btn btn-success"
                            :disabled="hasError || disabled" @click="submit">Save</button>
                        <button v-else type="button" class="btn btn-danger" :disabled="disabled" @click="remove">Confirm
                            deletion</button>
                        <button v-if="!willDelete" type="button" class="btn btn-outline-danger" :disabled="disabled"
                            @click="willDelete = !willDelete">Delete</button>
                        <button v-else type="button" class="btn btn-outline-secondary" :disabled="disabled"
                            @click="willDelete = !willDelete">Cancel</button>
                    </div>
                </template>
            </form-container>

            <div v-else>
                <p class="text-muted interactive-text">No suggestion channel defined. Create one first.</p>
            </div>

        </div>
    </div>
</template>
<script lang="ts" src="./SuggestionChannel.vue.ts"></script>
<style lang="scss" scoped>
    @import "~/../ts2/web/index/styles/colors";

    .suggestion-channel-tabs {
        display: flex;
        flex-flow: row wrap-reverse;

        margin: 0 0 1rem 0;
        padding: 0;

        .tab {
            display: block;
            margin: .5rem 0 0 0;
        }

        .btn {
            font-weight: 600;
            letter-spacing: -0.5px;
            border: none;
            border-bottom: 2px solid;
            border-radius: 0;
        }

        .active .btn {
            color: $color-accent;
            box-shadow: inset 0px -10px 10px -14px $color-accent;
        }
    }

    .suggestion-channel-options {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem 1.5rem;

        @media screen and (max-width: $display-width-large) {
            display: flex;
            flex-flow: column nowrap;
            gap: 0;

            &>:not(:first-child) {
                margin-top: 2rem;
            }
        }

        &.disabled {
            pointer-events: none;
            filter: opacity(.5);
        }
    }

    .emote-selection,
    .minimum-requirements {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: .75rem;
    }

    .reaction-list {
        padding: 0;

        display: flex;
        flex-flow: column nowrap;

        > :not(:first-child) {
            margin-block-start: .25rem;
        }
    }

    .reaction-row {
        display: flex;
        align-items: center;

        &:not(:first-child) {
            margin-block-start: 1rem;
        }
    }

    .reaction-pair {
        flex: 1 1 auto;
        margin-inline-start: .5rem;

        display: flex;
        flex-flow: row wrap;

        > :first-child {
            flex: 1 1 40%;
            margin-inline-end: .75rem;
        }

        > :not(:first-child) {
            flex: 2 1 auto;
        }
    }

    .suggestion-channel {
        display: flex;
        flex-flow: row nowrap;
        padding-block-end: 1rem;
        border-bottom: 1px dotted $hairline-color;
    }

    .suggestion-channel-select {
        flex: 1 0 auto;
    }

    .suggestion-channel-actions {
        display: flex;
        flex-flow: row wrap;

        > :not(:first-child) {
            margin-inline-start: .5rem;
        }

        >:first-child {
            flex: 1 0 auto;
        }
    }
</style>