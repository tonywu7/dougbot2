// importer.ts
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

import * as util from '../common/util'

let inputPathForm: HTMLFormElement
let inputPathSubmit: HTMLInputElement
let candidateForm: HTMLFormElement
let candidateList: HTMLDivElement
let candidateSubmit: HTMLInputElement

let notification: HTMLElement
let pollEndpoint: string
let cancelEndpoint: string

interface MediaCandidate {
    id: string
    path: string
    duration: number
    preview: string | null
    selected: boolean | null
}

function setButtonState(state: string) {
    switch (state) {
        case 'initial':
            inputPathSubmit.value = 'Scan'
            inputPathSubmit.className = ''
            inputPathSubmit.removeEventListener('click', cancel)
            inputPathSubmit.addEventListener('click', submitForScanning)
            break
        case 'parse':
        case 'scan':
            inputPathSubmit.value = 'Cancel'
            inputPathSubmit.className = 'color-danger-bg'
            inputPathSubmit.removeEventListener('click', submitForScanning)
            inputPathSubmit.addEventListener('click', cancel)
            break
    }
}

function flashMessage(msg: string | null, type: string = 'error') {
    if (!msg) {
        notification.textContent = ''
        notification.classList.add('hidden')
        return
    }
    notification.className = ''
    notification.classList.add(`color-${type}-fg`)
    notification.textContent = msg
}

function csrfPOSTOpts(extraHeaders: Record<string, string> | null = null): RequestInit {
    const csrftoken = (document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement)!.value
    let headers = Object.assign(
        {
            'X-CSRFToken': csrftoken,
        },
        extraHeaders
    )
    return {
        method: 'POST',
        headers: headers,
        credentials: 'same-origin',
    }
}

async function submitForScanning() {
    if (!inputPathForm.checkValidity()) {
        inputPathForm.reportValidity()
        return
    }
    setButtonState('scan')
    let controller = new AbortController()
    let res: Response
    let listener = () => {
        controller.abort()
        inputPathSubmit.removeEventListener('click', listener)
    }
    inputPathSubmit.addEventListener('click', listener)
    try {
        res = await fetch(
            inputPathForm.dataset.endpoint!,
            Object.assign(csrfPOSTOpts(), {
                body: new FormData(inputPathForm),
                signal: controller.signal,
            })
        )
    } catch (e) {
        flashMessage(`Server error: ${e}`)
        return
    }
    inputPathSubmit.removeEventListener('click', listener)
    if (res.status == 204) {
        return loadCandidates()
    } else {
        try {
            let info = await res.json()
            flashMessage(info.data.reason)
        } catch (e) {
            flashMessage(`Server error: Invalid response: ${e}`)
        }
        setButtonState('initial')
    }
}

function cancel() {
    fetch(cancelEndpoint, csrfPOSTOpts()).then(() => {
        setButtonState('initial')
    })
}

function loadCandidates() {
    resetCandidates()
    let pollInterval = setInterval(async () => {
        let res = await fetch(pollEndpoint)
        let data = await res.json()
        if (data.running === 0) {
            flashMessage('Importer is not running', 'warning')
            setButtonState('initial')
            clearInterval(pollInterval)
        } else if (data.running === 1) {
            flashMessage(`Scanning in progress (${data.found} found) ...`, 'info')
            setButtonState('scan')
        } else if (data.pending) {
            flashMessage(`${data.pending} remaining ...`, 'info')
            setButtonState('parse')
        } else {
            flashMessage('Scanning finished', 'success')
            setButtonState('initial')
            clearInterval(pollInterval)
        }
        initCandidates(data.data, data.base)
    }, 500)
}

function resetCandidates() {
    util.killAllChildren(document.querySelector('#import-candidates')! as HTMLDivElement)
}

function initCandidates(data: Array<MediaCandidate>, rootPath: string) {
    for (let media of data) {
        let row = util.getTemplate('import-candidate-template', '.import-candidate') as HTMLDivElement
        let label = row.querySelector('label')!
        let checkbox = (row.querySelector('.import-candidate-check') as HTMLInputElement)!
        let duration = (row.querySelector('.import-candidate-duration') as HTMLInputElement)!
        let preview = (row.querySelector('.preview-container') as HTMLDivElement)!
        let toggle = (row.querySelector('.import-preview-toggle a') as HTMLAnchorElement)!
        checkbox.id = checkbox.name = label.htmlFor = media.id
        checkbox.checked = false
        label.textContent = media.path
        checkbox.value = rootPath + '/' + media.path
        duration.name = `${media.id}-duration`
        duration.value = media.duration.toString()
        if (media.preview) {
            preview.innerHTML = media.preview
            toggle.addEventListener('click', (ev) => {
                ev.preventDefault()
                preview.classList.toggle('hidden')
            })
        }
        candidateList.append(row)
    }
}

export function init() {
    let container = document.querySelector('#importer-form-container') as HTMLDivElement
    if (!container) return

    inputPathForm = container.querySelector('form')! as HTMLFormElement
    inputPathSubmit = document.querySelector('#importer-scan')! as HTMLInputElement
    candidateForm = document.querySelector('#importer-scanned form')! as HTMLFormElement
    candidateList = document.querySelector('#import-candidates')! as HTMLDivElement
    candidateSubmit = document.querySelector('#importer-submit')! as HTMLInputElement
    notification = document.querySelector('#importer-notification')! as HTMLElement

    pollEndpoint = container.dataset.poll!
    cancelEndpoint = container.dataset.cancel!

    setButtonState('initial')

    let selectionHandlers = {
        '.importer-select-all': (e: Element) => ((e as HTMLInputElement).checked = true),
        '.importer-select-none': (e: Element) => ((e as HTMLInputElement).checked = false),
        '.importer-select-inverse': (e: Element) => {
            let elem = e as HTMLInputElement
            elem.checked = !elem.checked
        },
    }

    for (let [k, v] of Object.entries(selectionHandlers)) {
        document.querySelector(k)?.addEventListener('click', (ev) => {
            ev.preventDefault()
            candidateList.querySelectorAll('input[type="checkbox"]').forEach(v)
        })
    }
}
