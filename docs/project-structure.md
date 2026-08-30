# Project structure

```text
autocorrect2-hotstring-generation/
├── docs/
├── hotstring/
│   ├── autocorrect2/
│   │   ├── constants.py
│   │   ├── models.py
│   │   ├── parser.py
│   │   └── writer.py
│   ├── typo_generation/
│   │   ├── aggregation.py
│   │   ├── execution.py
│   │   ├── generation.py
│   │   └── models.py
│   ├── conflicts.py
│   ├── constants.py
│   ├── file_io.py
│   ├── models.py
│   ├── options.py
│   ├── pipeline.py
│   └── report.py
├── main.py
├── mkdocs.yml
└── pyproject.toml
```

Generic AutoHotkey behavior lives directly under `hotstring/`.
AutoCorrect2-specific knowledge is isolated under `hotstring/autocorrect2/`,
while typo generation remains independent under `hotstring/typo_generation/`.
