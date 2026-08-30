# Getting started

## Install

With `uv`:

```powershell
uv sync
uv sync --group docs
```

## Configure AutoCorrect2

Update `AUTOCORRECT2_PROJECT_DIR` in
`hotstring/autocorrect2/constants.py` or pass `project_dir` explicitly to the
pipeline functions.

Add a one-time `#Include` for `Core/GeneratedHotstrings.ahk` inside the same
`#HotIf AutoCorrectionsActivelyRunning()` context used by AutoCorrect2's main
autocorrection library.

## Build documentation

```powershell
uv run --group docs mkdocs serve
```

Add the four custom CSS files described in `mkdocs.yml` under
`docs/assets/stylesheets/` before serving the final themed documentation.
