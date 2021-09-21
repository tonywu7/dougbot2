import * as main from './main'
import * as server from './server'

import './styles/index.scss'

window.addEventListener('DOMContentLoaded', () => {
    main.init()
    server.init()
})
