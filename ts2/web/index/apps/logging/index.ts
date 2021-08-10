import { selectAndMount } from '../../components/utils/app'
import { LoggingConfig } from '../../server'
import Logging from './Logging.vue'

window.addEventListener('DOMContentLoaded', () => {
    let availableConf: Partial<LoggingConfig>[] = [
        ...document.querySelectorAll<HTMLElement>('.logging-conf'),
    ].map((e) => ({
        key: e.dataset.key!,
        name: e.dataset.name,
        superuser: Boolean(e.dataset.superuser),
    }))
    selectAndMount('#logging-config', Logging, { conf: availableConf })
})
