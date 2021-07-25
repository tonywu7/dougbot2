import { selectAndMount } from '../../components/utils/app'
import BugReport from './BugReport.vue'

window.addEventListener('DOMContentLoaded', () => {
    selectAndMount('#bug-report', BugReport)
})
