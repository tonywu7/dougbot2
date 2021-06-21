import * as main from './scripts/main'
import * as login from './scripts/login'
import * as coreSettings from './scripts/apps/core'
import * as constraintSettings from './scripts/apps/constraints'

import './styles/index.scss'

window.addEventListener('DOMContentLoaded', async () => {
    await login.init()
    main.init()
    coreSettings.init()
    constraintSettings.init()
})
