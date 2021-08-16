import * as _ from 'lodash'

export function randomIdentifier(
    length: number,
    from: string = '0123456789abcdefghijklmnopqrstuvwxyz-_'
): string {
    return _.sampleSize(from, length).join('')
}

export function slugify(text: string, toStrip: RegExp = /[\p{P}_]+/gu) {
    return text.replace(toStrip, ' ').trim().toLowerCase()
}

export function serializeFormData(data: FormData): Record<string, string> {
    let obj: Record<string, string> = {}
    for (let k of data.keys()) {
        obj[k] = data.get(k)!.toString()
    }
    return obj
}

export function safe(s: string): string {
    let span = document.createElement('span')
    span.textContent = s
    return span.innerHTML
}
