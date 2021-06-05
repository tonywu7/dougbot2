// main.ts
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

function setSocketStatus(connected: boolean) {
    let indicator = document.querySelector('#socket-status') as HTMLSpanElement
    if (indicator === null) return
    indicator.innerHTML = `<i class="bi bi-circle-fill"></i>${connected ? 'connected' : 'disconnected'}`
    if (connected) {
        indicator.classList.add('socket-on')
        indicator.classList.remove('socket-off')
    } else {
        indicator.classList.add('socket-off')
        indicator.classList.remove('socket-on')
    }
}

function initWebSocket(): Promise<boolean> {
    return new Promise((resolve, reject) => {
        let socket = new WebSocket(`ws://${window.location.host}/bot/ws/index/`)
        socket.addEventListener('open', () => {
            setSocketStatus(true)
            return resolve(true)
        })
        socket.addEventListener('message', (ev) => {
            console.log(ev.data)
        })
        socket.addEventListener('close', () => {
            setSocketStatus(false)
            setTimeout(initWebSocket, 1000)
        })
    })
}

export function init() {
    initWebSocket()
}
