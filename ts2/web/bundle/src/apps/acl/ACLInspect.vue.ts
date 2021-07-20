import { defineComponent, onMounted, ref, Ref } from 'vue'
import ItemSelect from '../../components/input/ItemSelect.vue'
import { Role, Channel, Command, server } from '../../server'

export default defineComponent({
    components: { ItemSelect },
    setup() {
        let roles: Ref<Role[]> = ref([])
        let channels: Ref<Channel[]> = ref([])
        let commands: Ref<Command[]> = ref([])
        onMounted(async () => {
            roles.value.push(...(await server.getRoles()))
            channels.value.push(...(await server.getChannels()))
            commands.value.push(...(await server.getCommands()))
        })
        return { roles, channels, commands }
    },
    data() {
        let result: string = '...'
        let selected: {
            roles: Role[]
            channel?: Channel
            command?: Command
        } = { roles: [] }
        return { result, selected }
    },
})
