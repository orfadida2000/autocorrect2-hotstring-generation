# Getting started

## Install

The project uses `uv` and is configured as a non-package project. A normal sync
installs the runtime dependency plus the default `dev` and `docs` groups:

```powershell
uv sync
```

## Configure AutoCorrect2

The project does not contain a machine-specific AutoCorrect2 path. Commands
which read AutoCorrect2 resolve the project directory in this order:

1. `--autocorrect2-project-dir`;
2. the `AUTOCORRECT2_PROJECT_DIR` process environment variable;
3. a dotenv file selected with `--env-file`;
4. `.env` at the repository root.

For normal local use, copy the committed example and edit the value:

```powershell
Copy-Item .env.example .env
```

```dotenv
AUTOCORRECT2_PROJECT_DIR=H:/Projects/AutoCorrect2
```

The local `.env` is ignored by Git. A relative path in a dotenv file is
resolved relative to that file. Relative command-line and process-environment
paths are resolved relative to the current working directory.

Add a one-time `#Include` for `Core/GeneratedHotstrings.ahk` in the same active
AutoCorrect2 hotstring context as the main autocorrection library. The generated
file remains project-owned and is scanned on later runs when it exists.

## Run a workflow

The command-line interface mirrors the three public pipeline functions:

```powershell
uv run python -m hotstring --help
```

For example, run the complete workflow with a UTF-8 file containing one source
word per non-empty line:

```powershell
uv run python -m hotstring full-pipeline `
    --words-file .\words.txt `
    --single-attempts 100 `
    --multi-attempts 100 `
    --multi-min-length 5 `
    --report .\hotstring-generation-report.txt
```

Those sampling values are examples rather than application defaults. The CLI
requires them so every run states its sampling policy explicitly. Use
`--write-accepted` to opt into modifying
`Core/GeneratedHotstrings.ahk`; without it, AutoCorrect2-aware workflows only
read and report.

Add `-v` before the workflow name for progress messages, or `-vv` for debugging
details:

```powershell
uv run python -m hotstring -v full-pipeline --help
```

## Build the documentation

```powershell
uv run mkdocs serve
```

The MkDocs configuration uses these committed stylesheet files under
`docs/assets/stylesheets/`:

- `catppuccin-latte.css`
- `catppuccin-mocha.css`
- `dracula.css`
- `extra.css`
