import { selectAndMount } from '../../components/utils/app'
import ACLInspect from './ACLInspect.vue'

window.addEventListener('DOMContentLoaded', () => {
    selectAndMount('#acl-inspect', ACLInspect)
})
