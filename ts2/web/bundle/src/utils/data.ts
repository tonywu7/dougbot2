import * as _ from 'lodash'

export function randomIdentifier(
    length: number,
    from: string = '0123456789abcdefghijklmnopqrstuvwxyz-_'
): string {
    return 'r' + _.sampleSize(from, length - 1).join('')
}

export function slugify(text: string, toStrip: RegExp = /[\W_]+/g) {
    return text.replace(toStrip, ' ').trim().toLowerCase()
}

export function serializeFormData(data: FormData): Record<string, string> {
    let obj: Record<string, string> = {}
    for (let k of data.keys()) {
        obj[k] = data.get(k)!.toString()
    }
    return obj
}
