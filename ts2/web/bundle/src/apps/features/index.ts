import './index.scss'

function highlightAnim() {
    if (!window.location.hash) return
    let elem = document.querySelector<HTMLElement>(window.location.hash)
    if (!elem) return
    elem.parentElement?.classList.remove('highlighted')
    document.documentElement.offsetWidth
    elem.parentElement?.classList.add('highlighted')
}

window.addEventListener('DOMContentLoaded', highlightAnim)
window.addEventListener('hashchange', highlightAnim)
