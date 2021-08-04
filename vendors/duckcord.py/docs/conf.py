import sphinx_rtd_theme  # noqa: F401

project = 'duckcord.py'
copyright = '2021, @tonywu7'
author = '@tonywu7'


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx_rtd_theme',
]

templates_path = ['_templates']

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'

html_static_path = ['_static']
html_css_files = [
    'css/index.css',
]

autoclass_content = 'both'

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'discord': ('https://discordpy.readthedocs.io/en/stable/', None),
    'attrs': ('https://www.attrs.org/en/stable/', None),
}
