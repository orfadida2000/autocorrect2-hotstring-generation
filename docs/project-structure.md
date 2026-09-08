# Project structure

```text
autocorrect2-hotstring-generation/
├── docs/
│   ├── api/
│   ├── concepts/
│   ├── configuration/
│   └── workflows/
├── hotstring/
│   ├── core/
│   │   ├── constants.py
│   │   ├── conflicts.py
│   │   ├── models.py
│   │   ├── options.py
│   │   └── trigger.py
│   ├── autocorrect2/
│   │   ├── source_loading/
│   │   │   ├── cache.py
│   │   │   ├── loader.py
│   │   │   └── parser.py
│   │   ├── constants.py
│   │   ├── integration.py
│   │   ├── models.py
│   │   └── writer.py
│   ├── typo_generation/
│   │   ├── aggregation.py
│   │   ├── execution.py
│   │   ├── generation.py
│   │   └── models.py
│   ├── constants.py
│   ├── file_io.py
│   ├── pipeline.py
│   └── report.py
├── main.py
├── mkdocs.yml
└── pyproject.toml
```

Generic AutoHotkey hotstring behavior lives under `hotstring/core/`.
AutoCorrect2-specific knowledge is isolated under `hotstring/autocorrect2/`,
with source loading further separated into its own subpackage. Typo generation
remains independent under `hotstring/typo_generation/`.

Top-level `hotstring` modules are reserved for project-level orchestration and
infrastructure rather than the generic hotstring domain model.
