// article.ts
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

import './article.scss'

import { flatten } from 'lodash'
import { slugify } from '../../utils/data'

function createLandmarks() {
    if (!document.body.classList.contains('article-view')) return
    let headings = flatten([
        ...[...document.querySelectorAll('article')].map((a) => [
            ...a.querySelectorAll<HTMLElement>('h1, h2, h3, h4, .landmark'),
        ]),
    ]) as HTMLElement[]
    for (let heading of headings) {
        if (heading.classList.contains('no-landmark')) continue
        let text = heading.textContent
        if (text) {
            let id = slugify(text).replace(/ /g, '-').replace(/-+/g, '-')
            let landmark = document.createElement('span')
            landmark.id = id
            landmark.setAttribute('role', 'presentation')
            landmark.classList.add('anchor-position')
            landmark.textContent = '\xa0'
            let anchor = document.createElement('a')
            anchor.id = `anchor-${id}`
            anchor.href = `#${id}`
            anchor.classList.add('anchor')
            anchor.setAttribute('aria-label', 'Jump to here')
            anchor.setAttribute('aria-hidden', 'true')
            anchor.innerHTML = '<i class="bi bi-link-45deg"></i>'
            heading.append(anchor)
            heading.append(landmark)
            heading.classList.add('anchor-container')
        }
    }
}

window.addEventListener('DOMContentLoaded', () => {
    createLandmarks()
})
