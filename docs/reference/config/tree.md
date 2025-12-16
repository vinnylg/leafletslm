# Configuration Module

::: drugslm.config.tree
    options:
        show_source: true

<!-- Show Private In Docs

::: my_package.my_module.MyClass
    options:
      filters: ["!^__"]  # Exclude __magic__ methods, but keep _private ones

::: my_package.my_module.MyClass
    options:
      filters: []  # No filters, show everything

Explicit List:

::: my_package.my_module.MyClass
    options:
      members:
        - _internal_helper_function
        - _private_variable
        - public_method

mkdocs.yaml
plugins:
  - mkdocstrings:
      handlers:
        python:
          options:
            # Change default filter to show private members globally
            filters: ["!^__"]
            show_if_no_docstring: true

Summary Regex:

- ["!^_[^_]"]: Default. Hides _private, shows public and __magic__.
- ["!^__"]: Shows public and _private, hides __magic__.
- []: Shows everything.

-->