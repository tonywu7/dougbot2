<template>
    <div class="form">
        <h4 class="title">Test out access control settings:</h4>
        <div>
            <item-select label="In channel" :items="channels" v-model:error="errors.channel" :multiple="false"
                v-model:choices="selected.channel">
            </item-select>
            <item-select label="Member with roles" :items="roles" v-model:choices="selected.roles">
            </item-select>
            <item-select label="Using command" :items="commands" v-model:error="errors.command" :multiple="false"
                v-model:choices="selected.command">
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
                        <span> to use command </span>
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
    .title {
        margin-top: 0;
    }

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

    .test-result {
        font-size: 1rem;
    }

    .result-arg {
        display: inline-block;
        text-decoration: 2px underline;
    }

    .bi-circle-fill::before {
        top: -2px;
    }
</style>