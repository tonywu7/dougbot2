<template>
    <div :class="['suggestion-channel-list-container', {'loading': loading}]">
        <div class="suggestion-channel-list">
            <transition-group name="fade">
                <form-container v-for="(suggest, index) in data" :key="suggest">
                    <template v-slot:form-fields>
                        <div class="suggestion-channel">
                            <item-select class="suggestion-channel-select" label="Channel" :items="channels"
                                v-model:choices="suggest._channels" :options="{multiple: false}">
                            </item-select>
                            <button type="button" class="btn btn-collapse" :class="[expanded(index) ? '' : 'show']"
                                @click="setExpanded(index)"><i class="bi bi-chevron-down"></i></button>
                        </div>
                        <transition name="fade">
                            <div class="suggestion-channel-options" v-show="expanded(index)">
                                <div class="form-fields">
                                    <div class="emote-selection">
                                        <item-select label="Upvote" :items="emotes" v-model:choices="suggest._upvotes"
                                            :options="{multiple: false, unsafe: true}" :factory="emoteFactory">
                                        </item-select>
                                        <item-select label="Downvote" :items="emotes"
                                            v-model:choices="suggest._downvotes"
                                            :options="{multiple: false, unsafe: true}" :factory="emoteFactory">
                                        </item-select>
                                        <item-select label="Approve" :items="emotes" v-model:choices="suggest._approves"
                                            :options="{multiple: false, unsafe: true}" :factory="emoteFactory">
                                        </item-select>
                                        <item-select label="Reject" :items="emotes" v-model:choices="suggest._rejects"
                                            :options="{multiple: false, unsafe: true}" :factory="emoteFactory">
                                        </item-select>
                                    </div>
                                    <input-field type="checkbox" name="requiresText" label="suggestion requires text"
                                        :id="`suggest-channel-${index}-requires-text`"
                                        v-model:value="suggest.requiresText">
                                    </input-field>
                                </div>
                                <div class="form-fields">
                                    <input-field type="textarea" name="description"
                                        :id="`suggest-channel-${index}-description`"
                                        v-model:value="suggest.description">
                                    </input-field>
                                    <div class="minimum-requirements">
                                        <input-field type="number" name="requiresUploads" label="minimum # of files"
                                            :id="`suggest-channel-${index}-requires-uploads`"
                                            v-model:value="suggest.requiresUploads">
                                        </input-field>
                                        <input-field type="number" name="requiresLinks" label="minimum # of links"
                                            :id="`suggest-channel-${index}-requires-links`"
                                            v-model:value="suggest.requiresLinks">
                                        </input-field>
                                    </div>
                                </div>
                            </div>
                        </transition>
                    </template>
                </form-container>
            </transition-group>
        </div>
        <div class="suggestion-channel-actions">
            <button type="button" class="btn btn-success btn-new" @click="createChannel">Add a new suggestion
                channel</button>
            <button type="button" class="btn btn-primary" @click="submit">Save changes</button>
        </div>
    </div>
</template>
<script lang="ts" src="./SuggestionChannelList.vue.ts"></script>
<style lang="scss" scoped>
    .suggestion-channel-options {
        display: grid;
        gap: 1rem;
        grid-template-columns: 1fr 1fr;
    }

    .emote-selection {
        display: grid;
        gap: .5rem;
        grid-template-columns: 1fr 1fr;
    }

    .minimum-requirements {
        display: grid;
        gap: .5rem;
        grid-template-columns: 1fr 1fr;
    }

    .suggestion-channel-list-container {
        display: flex;
        flex-flow: column nowrap;

        > :not(:first-child) {
            margin-block-start: 1rem;
        }
    }

    .suggestion-channel-list {
        display: flex;
        flex-flow: column nowrap;

        > :not(:first-child) {
            margin-block-start: 1rem;
        }
    }

    .suggestion-channel-actions {
        display: flex;
        flex-flow: row wrap;
        gap: .5rem;

        .btn-new {
            flex: 1 0 auto;
        }
    }

    .suggestion-channel {
        display: flex;
        flex-flow: row nowrap;
    }

    .suggestion-channel-select {
        flex: 1 0 auto;
    }

    .btn-collapse {
        font-size: 1.5rem;
        color: inherit;
        margin: 0 .5rem 0 1rem;

        transition: transform .3s ease;

        &.show {
            transform: rotate(180deg);
        }
    }
</style>