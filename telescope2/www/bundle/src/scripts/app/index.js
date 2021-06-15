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

const MODULES = ['./main', './apps/core', './apps/constraints']

window.addEventListener('DOMContentLoaded', () => {
    let mainScript = document.getElementById('script-entry')
    let staticServer = mainScript.dataset.server
    requirejs.config({
        baseUrl: `${staticServer}/static/bundle/scripts/app`,
        paths: {
            bootstrap: 'https://cdn.jsdelivr.net/npm/bootstrap@5.0.1/dist/js/bootstrap.bundle.min',
            lodash: 'https://cdn.jsdelivr.net/npm/lodash@4.17.20/lodash.min',
            mustache: 'https://cdn.jsdelivr.net/npm/mustache@4.2.0/mustache.min',
            d3: 'https://cdnjs.cloudflare.com/ajax/libs/d3/7.0.0/d3.min',
            lunr: 'https://cdnjs.cloudflare.com/ajax/libs/lunr.js/2.3.9/lunr.min',
        },
        deps: ['bootstrap', 'lodash', 'd3', 'mustache', 'lunr'],
        onNodeCreated: (node, config, module, path) => {
            const SRI = {
                bootstrap: 'sha384-gtEjrD/SeCtmISkJkNUaaKMoLD0//ElJ19smozuHV6z3Iehds+3Ulb9Bn9Plx0x4',
                lodash: 'sha256-ur/YlHMU96MxHEsy3fHGszZHas7NzH4RQlD4tDVvFhw=',
                mustache: 'sha256-1/0GA1EkYejtvYFoa+rSq4LfM4m5zKI13Z1bQIhI4Co=',
                d3: 'sha512-0x7/VCkKLLt4wnkFqI8Cgv6no+AaS1TDgmHLOoU3hy/WVtYta2J6gnOIHhYYDJlDxPqEqAYLPS4gzVex4mGJLw==',
                lunr: 'sha512-4xUl/d6D6THrAnXAwGajXkoWaeMNwEKK4iNfq5DotEbLPAfk6FSxSP3ydNxqDgCw1c/0Z1Jg6L8h2j+++9BZmg==',
            }
            if (SRI[module]) {
                node.setAttribute('integrity', SRI[module])
                node.setAttribute('crossorigin', 'anonymous')
                node.setAttribute('referrerpolicy', 'no-referrer')
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
