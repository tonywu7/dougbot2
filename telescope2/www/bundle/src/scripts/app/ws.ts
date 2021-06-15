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
        socket.addEventListener('message', (ev) => {})
        socket.addEventListener('close', () => {
            setSocketStatus(false)
            setTimeout(initWebSocket, 1000)
        })
    })
}
