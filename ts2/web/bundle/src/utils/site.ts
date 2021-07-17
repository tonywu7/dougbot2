export function homepage(): string {
    return document.querySelector<HTMLAnchorElement>('#site-name a')!.href
}

export function getCSRF(elem: HTMLElement) {
    let csrf = elem.querySelector<HTMLInputElement>(
        'input[type="hidden"][name="csrfmiddlewaretoken"]'
    )
    if (!csrf) {
        throw new Error(`No CSRF token found for form ${elem}`)
    }
    return csrf.value
}
