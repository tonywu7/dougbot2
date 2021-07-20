<template>
    <!-- <div class="form">
        <input-field type="text" name="name" v-model:value="name" v-model:error="error">
        </input-field>
        <item-select label="Where" :items="channels" v-model:choices="selected.channels"
            placeholder="type in the name of a channel">
        </item-select>
        <item-select label="What" :items="commands" v-model:choices="selected.commands" placeholder="type in a command">
        </item-select>
        <item-select label="Who" :items="roles" v-model:choices="selected.roles"
            placeholder="type in the name of a role">
        </item-select>
    </div> -->
    <div>
        <input-select :options="options" v-model:value="value"></input-select>
    </div>
</template>
<script lang="ts" src="./ACLList.vue.ts"></script>