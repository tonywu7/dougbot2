import { computed } from 'vue'

export function modelValueWithEmit<T>(
    props: Record<string, any>,
    emit: (event: string, ...args: any) => void,
    name: string
) {
    return computed<T>({
        get: () => props[name],
        set: (v) => {
            emit(`update:${name}`, v)
        },
    })
}
