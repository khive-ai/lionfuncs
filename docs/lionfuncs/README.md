# lionfuncs Documentation

This directory contains the documentation for the `lionfuncs` package.

## Documentation Structure

- [**index.md**](index.md): Overview, installation, and quick start guide.
- [**api/**](api/): API reference documentation.
  - [**index.md**](api/index.md): Overview of the API reference.
  - [**utils.md**](api/utils.md): Documentation for the `utils` module.
  - [**errors.md**](api/errors.md): Documentation for the `errors` module.
  - [**file_system/**](api/file_system/): Documentation for the `file_system`
    module.
    - [**index.md**](api/file_system/index.md): Overview of the `file_system`
      module.
    - [**core.md**](api/file_system/core.md): Documentation for the
      `file_system.core` module.
    - [**media.md**](api/file_system/media.md): Documentation for the
      `file_system.media` module.
  - [**concurrency.md**](api/concurrency.md): Documentation for the
    `concurrency` module.
  - [**async_utils.md**](api/async_utils.md): Documentation for the
    `async_utils` module.
  - [**network/**](api/network/): Documentation for the `network` module.
    - [**index.md**](api/network/index.md): Overview of the `network` module.
    - [**client.md**](api/network/client.md): Documentation for the
      `network.client` module.
    - [**resilience.md**](api/network/resilience.md): Documentation for the
      `network.resilience` module.
    - [**adapters.md**](api/network/adapters.md): Documentation for the
      `network.adapters` module.
    - [**primitives.md**](api/network/primitives.md): Documentation for the
      `network.primitives` module.
- [**guides/**](guides/): Usage guides and tutorials.
  - [**async_operations.md**](guides/async_operations.md): Guide to async
    operations with alcall/bcall.
  - [**network_client.md**](guides/network_client.md): Guide to using
    AsyncAPIClient with resilience patterns.
- [**contributing.md**](contributing.md): Guidelines for contributing to the
  project.

## Building the Documentation

The documentation is written in Markdown format and can be built using a variety
of tools:

### Using MkDocs

1. Install MkDocs and the Material theme:

```bash
pip install mkdocs mkdocs-material
```

2. Create an `mkdocs.yml` file in the root directory:

```yaml
site_name: lionfuncs Documentation
site_description: Documentation for the lionfuncs package
site_author: khive-ai

theme:
  name: material
  palette:
    primary: indigo
    accent: indigo
  features:
    - navigation.tabs
    - navigation.sections
    - toc.integrate
    - search.suggest
    - search.highlight
    - content.tabs.link

markdown_extensions:
  - pymdownx.highlight
  - pymdownx.superfences
  - pymdownx.inlinehilite
  - pymdownx.tabbed
  - pymdownx.critic
  - pymdownx.tasklist:
      custom_checkbox: true
  - admonition
  - toc:
      permalink: true

nav:
  - Home: lionfuncs/index.md
  - API Reference:
      - Overview: lionfuncs/api/index.md
      - utils: lionfuncs/api/utils.md
      - errors: lionfuncs/api/errors.md
      - file_system:
          - Overview: lionfuncs/api/file_system/index.md
          - core: lionfuncs/api/file_system/core.md
          - media: lionfuncs/api/file_system/media.md
      - concurrency: lionfuncs/api/concurrency.md
      - async_utils: lionfuncs/api/async_utils.md
      - network:
          - Overview: lionfuncs/api/network/index.md
          - client: lionfuncs/api/network/client.md
          - resilience: lionfuncs/api/network/resilience.md
          - adapters: lionfuncs/api/network/adapters.md
          - primitives: lionfuncs/api/network/primitives.md
  - Guides:
      - Async Operations: lionfuncs/guides/async_operations.md
      - Network Client: lionfuncs/guides/network_client.md
  - Contributing: lionfuncs/contributing.md
```

3. Build the documentation:

```bash
mkdocs build
```

4. Serve the documentation locally:

```bash
mkdocs serve
```

### Using Sphinx

1. Install Sphinx and the required extensions:

```bash
pip install sphinx sphinx-rtd-theme myst-parser
```

2. Create a `conf.py` file in the `docs` directory:

```python
# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'lionfuncs'
copyright = '2025, khive-ai'
author = 'khive-ai'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------
myst_enable_extensions = [
    'colon_fence',
]

source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}
```

3. Create an `index.rst` file in the `docs` directory:

```rst
lionfuncs Documentation
=======================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   lionfuncs/index
   lionfuncs/api/index
   lionfuncs/guides/async_operations
   lionfuncs/guides/network_client
   lionfuncs/contributing
```

4. Build the documentation:

```bash
sphinx-build -b html docs docs/_build/html
```

5. View the documentation:

```bash
open docs/_build/html/index.html
```

## Contributing to the Documentation

If you'd like to contribute to the documentation, please follow these
guidelines:

1. Use Markdown format for all documentation files.
2. Follow the existing structure and style.
3. Include examples for all functions, classes, and methods.
4. Use relative links for internal references.
5. Test all code examples to ensure they work as expected.

See the [contributing guide](contributing.md) for more information on
contributing to the project.
