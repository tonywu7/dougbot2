function appendEmptyFormset() {
    let formCountInput = document.querySelector<HTMLInputElement>('#id_form-TOTAL_FORMS')!
    let formCount = Number(formCountInput.value)
    let prefix = formCount
    formCountInput.value = (prefix + 1).toString()
    let formList = document.querySelector<HTMLTableSectionElement>('#result_list tbody')!
    let emptyForm = document.querySelector<HTMLElement>('.empty-form')!
    let inputs = emptyForm.querySelectorAll<HTMLInputElement>('[name^="form-__prefix__"]')
    let fields: HTMLElement[] = []
    let row = document.createElement('tr')
    row.id = `formset-new-item-${prefix}`
    let checkbox = document.createElement('td')
    checkbox.classList.add('action-checkbox')
    let pk = document.createElement('th')
    pk.classList.add('field-pk')
    let remove = document.createElement('a')
    remove.classList.add('text-danger')
    remove.innerHTML = '<i class="bi bi-trash-fill"></i>'
    remove.href = '#'
    remove.addEventListener('click', () => {
        row.remove()
    })
    pk.append(remove)
    for (let input of inputs) {
        let fieldName = input.name.replace(/form-__prefix__-/, '')
        input = input.cloneNode(true) as HTMLInputElement
        input.id = `id_form-${prefix}-${fieldName}`
        input.name = `form-${prefix}-${fieldName}`
        if (input.type == 'hidden') {
            pk.append(input)
            continue
        }
        let container = document.createElement('td')
        container.classList.add(`field-${fieldName}`)
        container.append(input)
        fields.push(container)
    }
    row.append(checkbox, pk, ...fields)
    formList.append(row)
}

export function init() {
    document.querySelector<HTMLButtonElement>('.btn-new')?.addEventListener('click', appendEmptyFormset)
}
