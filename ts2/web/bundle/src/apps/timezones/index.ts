import { selectAndMount } from '../../components/utils/app'
import TimezoneList from './TimezoneList.vue'

window.addEventListener('DOMContentLoaded', () => {
    selectAndMount('#timezone-list', TimezoneList)
})
