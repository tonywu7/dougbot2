const graphql = require('graphql')

/**
 *
 * @param {string|Buffer} content Content of the resource file
 * @param {object} [map] SourceMap data consumable by https://github.com/mozilla/source-map
 * @param {any} [meta] Meta data, could be anything
 */
module.exports = function stripCharLoader(content, map, meta) {
    return graphql.stripIgnoredCharacters(content)
}
