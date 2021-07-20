import { selectAndMount } from '../../components/utils/app'
import ACLInspect from './ACLInspect.vue'
import ACLList from './ACLList.vue'

window.addEventListener('DOMContentLoaded', () => {
    selectAndMount('#acl-inspect', ACLInspect)
    selectAndMount('#acl-list', ACLList)
})
