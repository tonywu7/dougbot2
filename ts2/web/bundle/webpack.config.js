'use strict'
const { readdirSync } = require('fs')
const path = require('path')
const { DefinePlugin } = require('webpack')
const { VueLoaderPlugin } = require('vue-loader')

const devMode = process.env.NODE_ENV !== 'production'

const BASE = path.resolve(__dirname)
const SOURCE = path.resolve(BASE, 'src')
const DEST = path.resolve(BASE, 'build', 'telescope2')
const APP_ROOT = path.resolve(SOURCE, 'apps')

const APPS = readdirSync(APP_ROOT, { withFileTypes: true })
  .filter((d) => d.isDirectory())
  .map((d) => ({ [d.name]: path.resolve(APP_ROOT, d.name, 'index.ts') }))

module.exports = {
  mode: devMode ? 'development' : 'production',
  target: 'web',
  context: path.resolve(__dirname),
  entry: Object.assign(
    {
      index: path.resolve(SOURCE, 'index.ts'),
    },
    ...APPS
  ),

  devtool: devMode ? 'source-map' : false,
  watch: devMode,

  module: {
    rules: [
      {
        test: /\.tsx?$/,
        loader: 'ts-loader',
        exclude: /node_modules/,
        options: {
          appendTsSuffixTo: [/\.vue$/],
        },
        sideEffects: false,
      },
      {
        test: /\.scss$/,
        use: ['style-loader', 'css-loader', 'sass-loader'],
        sideEffects: true,
      },
      {
        test: /\.(graphql|gql)$/,
        use: 'graphql-tag/loader',
        exclude: /node_modules/,
        sideEffects: false,
      },
      {
        test: /\.vue$/,
        use: 'vue-loader',
        sideEffects: false,
      },
      {
        test: /\.vue$/,
        resourceQuery: /type=style/,
        sideEffects: true,
      },
    ],
  },

  externals: devMode
    ? {}
    : {
        bootstrap: 'bootstrap',
        d3: 'd3',
        lunr: 'lunr',
        lodash: '_',
        vue: 'Vue',
      },

  plugins: [
    new DefinePlugin({
      __VUE_OPTIONS_API__: true,
      __VUE_PROD_DEVTOOLS__: false,
    }),
    new VueLoaderPlugin(),
  ],

  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
  },

  optimization: {
    usedExports: true,
    splitChunks: {
      cacheGroups: {
        vendors: {
          test: /\/node_modules\//,
          priority: -10,
          reuseExistingChunk: true,
          chunks: 'all',
          name: 'vendor',
        },
      },
    },
    runtimeChunk: 'single',
  },

  output: {
    path: DEST,
    filename: `[name].bundle.js`,
    clean: true,
  },

  stats: 'detailed',
}
