<template>
    <div class="form">
        <h4>Test out access control settings:</h4>
        <div>
            <item-select label="Member with roles" :items="roles" v-model:choices="selected.roles"
                placeholder="type in the name of a role">
            </item-select>
            <item-select label="Using command" :items="commands" v-model:error="errors.commands"
                v-model:choices="selected.commands" placeholder="type in a command" :multiple="false">
            </item-select>
            <item-select label="In channel" :items="channels" v-model:error="errors.channels"
                v-model:choices="selected.channels" placeholder="type in the name of a channel" :multiple="false">
            </item-select>
            <div class="test">
                <button type="button" class="btn btn-outline-primary btn-submit" @click="runTest">Test</button>
                <h4 class="test-result">
                    <template v-if="state === undefined">
                        <span>...</span>
                    </template>
                    <template v-else>
                        <span>This member is </span>
                        <span v-if="state === true" class="text-on">
                            <i class="bi bi-circle-fill"></i> allowed
                        </span>
                        <span v-else class="text-off">
                            <i class="bi bi-circle-fill"></i> not allowed
                        </span>
                        <span> to use </span>
                        <span class="result-arg" v-html="command"></span>
                        <span> in </span>
                        <span class="result-arg" :style="channelColor" v-html="channel"></span>
                    </template>
                </h4>
            </div>
        </div>
    </div>
</template>
<script lang="ts" src="./ACLInspect.vue.ts"></script>
<style lang="scss" scoped>
    .item-select {
        margin: .8rem 0;
    }

    .test {
        display: flex;
        flex-flow: row nowrap;
        align-items: center;
        gap: .6rem;

        .btn {
            width: min-content;
            margin: 0;
        }

        .test-result {
            margin: 0;
        }
    }

    .result-arg {
        text-decoration: 2px underline;
    }

    .bi-circle-fill::before {
        margin-inline-start: 1px;
        top: -2px;
    }
</style>