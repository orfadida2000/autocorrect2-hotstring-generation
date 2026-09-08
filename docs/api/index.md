# API reference

The API reference mirrors the Python package hierarchy and is rendered directly
from source docstrings with mkdocstrings.

- `hotstring.core` contains generic AutoHotkey hotstring behavior.
- `hotstring.autocorrect2` contains AutoCorrect2-specific integration, including
  the nested `source_loading` subpackage.
- `hotstring.typo_generation` contains typo-generation functionality.
- Top-level `hotstring` modules such as `pipeline`, `report`, and `file_io` are
  documented directly under this API section.

The conceptual and workflow documentation should be used for architectural
context; these pages focus on concrete Python symbols and signatures.
