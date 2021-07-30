import './index.scss'

function highlightAnim() {
    if (!window.location.hash) return
    let elem = document.querySelector<HTMLElement>(window.location.hash)
    if (!elem) return
    elem.parentElement?.classList.remove('highlighted')
    document.documentElement.offsetWidth
    elem.parentElement?.classList.add('highlighted')
}

window.addEventListener('hashchange', highlightAnim)
window.addEventListener('DOMContentLoaded', highlightAnim)
window.addEventListener('DOMContentLoaded', () => {
    let titles = {
        'status-01-PL':
            'There are plans to make this a feature, but no work has been done yet',
        'status-02-PR': 'Feature is the current focus of development',
        'status-03-PS':
            'Feature has some of its functionality implemented and is usable, but expect bugs and breaking changes',
        'status-04-RC':
            "Feature is considered stable and part of the bot's functionality",
        'status-05-FN':
            'Feature is stable and there are no plan to change any more of it',
        'status-10-SU': 'Feature has been replaced by another feature',
        'status-20-SP':
            'Feature is in its conceptual stage and no concrete plan exists for how to develop it',
        'status-30-NO': 'Feature will not be implemented',
        'status-31-NA':
            'This could be a feature but is currently impossible because of a lack of APIs or tools',
        'status-32-RM': 'This was a stable feature but is now removed',
        'status-33-ST':
            'This was a planned feature but its development has stopped',
    }
    for (let [cls, title] of Object.entries(titles)) {
        document
            .querySelectorAll<HTMLElement>(`.${cls}`)
            .forEach((e) => (e.title = title))
    }
})
