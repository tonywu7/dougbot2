const { rm } = require('fs/promises')
const { generate } = require('@graphql-codegen/cli')
const { Types } = require('@graphql-codegen/plugin-helpers')
const path = require('path')
const glob = require('glob-promise')

/**
 *
 * @param {string} base
 */
async function clean(base) {
    let types = await glob(path.resolve(base, '**/@types/graphql'))
    await Promise.all(types.map((p) => rm(p, { recursive: true })))
}

/**
 *
 * @param {string} src
 * @param {string} base
 * @returns {Promise<Types.Config>}
 */
async function buildOptions(src, base) {
    let documents = await glob(path.resolve(base, '**/graphql/'))
    /** @type {Types.Config} */
    let config = { schema: src, generates: {} }
    for (let d of documents) {
        let outdir = path.resolve(d, '..', '@types', 'graphql')
        let schemaDef = path.resolve(outdir, 'schema.ts')
        config.generates[schemaDef] = {
            documents: `${d}/**/*.graphql`,
            plugins: ['typescript', 'typescript-operations'],
            config: { namingConvention: 'keep' },
        }
    }
    return config
}

async function main() {
    let [src, base] = process.argv.slice(2)
    await clean(base)
    let config = await buildOptions(src, base)
    await generate(config, true)
}

main()
