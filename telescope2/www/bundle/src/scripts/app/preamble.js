function logout() {
    let userInfoElem = document.querySelector('#user-info')
    if (userInfoElem === null) return
    let accessToken = userInfoElem.dataset.accessToken
    if (!accessToken || accessToken === 'None') {
        window.location.href = '/web/logout'
    }
    fetch('https://discord.com/api/users/@me', {
        method: 'GET',
        mode: 'cors',
        headers: {
            Authorization: `Bearer ${accessToken}`,
        },
    }).then((r) => {
        if (r.status >= 400) window.location.href = '/web/logout'
    })
}

window.addEventListener('DOMContentLoaded', () => {
    logout()
})
