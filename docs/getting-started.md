# Getting started

## Install

The project uses `uv` and is configured as a non-package project. A normal sync
installs the runtime dependency plus the default `dev` and `docs` groups:

```powershell
uv sync
```

## Configure AutoCorrect2

Update
[`AUTOCORRECT2_PROJECT_DIR`][hotstring.autocorrect2.constants.AUTOCORRECT2_PROJECT_DIR]
in `hotstring/autocorrect2/constants.py`, or pass the AutoCorrect2 project path
to the relevant pipeline API when supported.

Add a one-time `#Include` for `Core/GeneratedHotstrings.ahk` in the same active
AutoCorrect2 hotstring context as the main autocorrection library. The generated
file remains project-owned and is scanned on later runs when it exists.

## Build the documentation

```powershell
uv run mkdocs serve
```

The MkDocs configuration references these custom stylesheet files under
`docs/assets/stylesheets/`:

- `catppuccin-latte.css`
- `catppuccin-mocha.css`
- `dracula.css`
- `extra.css`

Add those files before serving the final themed documentation.
