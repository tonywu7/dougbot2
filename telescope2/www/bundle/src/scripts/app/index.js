// index.js
// Copyright (C) 2021  @tonyzbf +https://github.com/tonyzbf/
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

const MODULES = ['./main']

window.addEventListener('DOMContentLoaded', () => {
    let mainScript = document.getElementById('script-entry')
    let staticServer = mainScript.dataset.server
    requirejs.config({
        baseUrl: `${staticServer}/static/bundle/scripts/app`,
        paths: {
            lodash: 'https://cdn.jsdelivr.net/npm/lodash@4.17.20/lodash.min',
        },
        deps: ['lodash'],
        onNodeCreated: (node, config, module, path) => {
            const SRI = {
                lodash: 'sha256-ur/YlHMU96MxHEsy3fHGszZHas7NzH4RQlD4tDVvFhw=',
            }
            if (SRI[module]) {
                node.setAttribute('integrity', SRI[module])
                node.setAttribute('crossorigin', 'anonymous')
            }
        },
    })
    require(MODULES, (...module) => {
        for (let i = 0, l = module.length; i < l; i++) {
            module[i].init()
        }
    })
})

window.addEventListener('load', () => {
    require(MODULES, (...module) => {
        for (let i = 0, l = module.length; i < l; i++) {
            let lateInit = module[i].lateInit
            if (lateInit) lateInit()
        }
    })
})
