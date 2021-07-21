import { selectAndMount } from '../../components/utils/app'
import App from './App.vue'

window.addEventListener('DOMContentLoaded', () => {
    selectAndMount('#acl-app', App)
})
