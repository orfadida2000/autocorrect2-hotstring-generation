# Project structure

???+ example "Project Structure"

    ```text
    autocorrect2-hotstring-generation/
    ├── docs/
    │   ├── index.md
    │   ├── api/
    │   │   ├── index.md
    │   │   ├── cli/
    │   │   │   ├── index.md
    │   │   │   ├── application.md
    │   │   │   ├── commands.md
    │   │   │   ├── parser.md
    │   │   │   └── runtime.md
    │   │   ├── core/
    │   │   │   ├── index.md
    │   │   │   ├── conflicts.md
    │   │   │   ├── constants.md
    │   │   │   ├── models.md
    │   │   │   ├── options.md
    │   │   │   └── trigger.md
    │   │   ├── autocorrect2/
    │   │   │   ├── index.md
    │   │   │   ├── source_loading/
    │   │   │   │   ├── index.md
    │   │   │   │   ├── cache.md
    │   │   │   │   ├── loader.md
    │   │   │   │   └── parser.md
    │   │   │   ├── constants.md
    │   │   │   ├── integration.md
    │   │   │   ├── models.md
    │   │   │   └── writer.md
    │   │   ├── typo-generation/
    │   │   │   ├── index.md
    │   │   │   ├── aggregation.md
    │   │   │   ├── execution.md
    │   │   │   ├── generation.md
    │   │   │   └── models.md
    │   │   ├── constants.md
    │   │   ├── file-io.md
    │   │   ├── pipeline.md
    │   │   └── report.md
    │   ├── assets/
    │   │   ├── icons/
    │   │   │   ├── ACicon.ico
    │   │   │   └── autocorrect2-spellcheck.svg
    │   │   ├── scripts/
    │   │   │   └── header-title-link.js
    │   │   └── stylesheets/
    │   │       ├── dracula.css
    │   │       └── extra.css
    │   ├── concepts/
    │   │   ├── index.md
    │   │   ├── autocorrect2.md
    │   │   ├── conflict-detection.md
    │   │   ├── hotstrings.md
    │   │   └── typo-generation.md
    │   ├── configuration/
    │   │   ├── index.md
    │   │   ├── autocorrect2.md
    │   │   └── typo-generation.md
    │   ├── workflows/
    │   │   ├── index.md
    │   │   ├── autocorrect2-check.md
    │   │   ├── full-pipeline.md
    │   │   ├── reporting.md
    │   │   └── typo-generation.md
    │   ├── command-line.md
    │   ├── getting-started.md
    │   ├── license.md
    │   ├── project-background.md
    │   └── project-structure.md
    ├── hotstring/
    │   ├── __init__.py
    │   ├── __main__.py
    │   ├── cli/
    │   │   ├── __init__.py
    │   │   ├── application.py
    │   │   ├── commands.py
    │   │   ├── parser.py
    │   │   └── runtime.py
    │   ├── core/
    │   │   ├── __init__.py
    │   │   ├── conflicts.py
    │   │   ├── constants.py
    │   │   ├── models.py
    │   │   ├── options.py
    │   │   └── trigger.py
    │   ├── autocorrect2/
    │   │   ├── __init__.py
    │   │   ├── source_loading/
    │   │   │   ├── __init__.py
    │   │   │   ├── cache.py
    │   │   │   ├── loader.py
    │   │   │   └── parser.py
    │   │   ├── constants.py
    │   │   ├── integration.py
    │   │   ├── models.py
    │   │   └── writer.py
    │   ├── typo_generation/
    │   │   ├── __init__.py
    │   │   ├── aggregation.py
    │   │   ├── execution.py
    │   │   ├── generation.py
    │   │   └── models.py
    │   ├── constants.py
    │   ├── file_io.py
    │   ├── pipeline.py
    │   └── report.py
    ├── .env.example
    ├── .gitignore
    ├── LICENSE
    ├── mkdocs.yml
    ├── pyproject.toml
    ├── README.md
    └── uv.lock
    ```

Generic AutoHotkey hotstring behavior lives under `hotstring/core/`.
AutoCorrect2-specific knowledge is isolated under `hotstring/autocorrect2/`,
with source loading further separated into its own subpackage. Typo generation
remains independent under `hotstring/typo_generation/`.

The `hotstring.cli` subpackage forms the command-line application layer:

- `parser.py` defines command-line syntax;
- `runtime.py` resolves external input and constructs runtime command objects;
- `commands.py` dispatches those objects to the public pipelines;
- `application.py` owns logging, process-level errors, and exit statuses;
- `__init__.py` re-exports `main`.

The `hotstring.__main__` module provides the `python -m hotstring` entry point
and delegates command-line execution to `hotstring.cli.application.main`. Other top-level
`hotstring` modules remain responsible for project-level orchestration and
infrastructure rather than the generic hotstring domain model.
