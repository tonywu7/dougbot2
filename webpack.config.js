'use strict'
const path = require('path')
const glob = require('glob')

const { DefinePlugin } = require('webpack')
const { VueLoaderPlugin } = require('vue-loader')
const { WebpackManifestPlugin } = require('webpack-manifest-plugin')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')

const devMode = process.env.NODE_ENV !== 'production'

const BASE = path.resolve(__dirname)
const PROJECT = BASE
const SOURCE = path.resolve(BASE, 'ts2')
const DEST = path.resolve(PROJECT, 'build', 'ts2')
const APPS = Object.assign(
  {},
  ...glob
    .sync(`${SOURCE}/**/index.ts`)
    .map((p) => ({ [path.basename(path.resolve(p, '..'))]: p }))
)

module.exports = {
  mode: devMode ? 'development' : 'production',
  target: 'web',
  context: path.resolve(__dirname),
  entry: APPS,

  devtool: devMode ? 'inline-source-map' : false,
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
        use: devMode
          ? ['style-loader', 'css-loader', 'sass-loader']
          : [MiniCssExtractPlugin.loader, 'css-loader', 'sass-loader'],
        sideEffects: true,
      },
      {
        test: /\.(graphql|gql)$/,
        use: [
          'graphql-tag/loader',
          { loader: path.resolve('./scripts/graphql-strip-char-loader.js') },
        ],
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
    ...(devMode
      ? []
      : [
          new MiniCssExtractPlugin({
            filename: `[name].[contenthash:8].css`,
          }),
        ]),
    new WebpackManifestPlugin({
      fileName: '../manifest.json',
    }),
  ],

  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
    alias: {
      web: path.resolve(__dirname, 'ts2', 'web', 'index'),
    },
  },

  optimization: {
    usedExports: true,
    splitChunks: {
      cacheGroups: {
        vendors: {
          test: /\/node_modules\//,
          priority: -10,
          chunks: 'all',
          reuseExistingChunk: true,
          name: 'vendor',
        },
      },
    },
    runtimeChunk: 'single',
  },

  output: {
    path: DEST,
    publicPath: 'ts2/',
    filename: `[name].[contenthash:8].js`,
    clean: true,
  },
}
