# AutoCorrect2 Hotstring Generation

Generate plausible keyboard-typo hotstrings with MULTYPO, remove internally
ambiguous mappings, validate the remaining candidates against active
AutoCorrect2 hotstrings, and optionally append accepted entries to a dedicated
generated AutoHotkey include file.

The project exposes three independent workflows through both Python APIs and
matching CLI subcommands:

1. standalone typo generation with `typo-generation`;
2. standalone AutoCorrect2 conflict checking with `autocorrect2-check`;
3. the composed workflow with `full-pipeline`.

## Getting started

The project targets Python 3.12+ and uses `uv` as a non-package project.

Install the runtime dependencies and the default development and documentation
groups:

```powershell
uv sync
```

Display the available CLI workflows:

```powershell
uv run python -m hotstring --help
```

Display the arguments for a specific workflow:

```powershell
uv run python -m hotstring full-pipeline --help
```

## Configure AutoCorrect2

The AutoCorrect2 project directory is resolved in this order:

1. `--project-dir PATH`;
2. the process environment variable `AUTOCORRECT2_PROJECT_DIR`;
3. the dotenv file selected by `--env-file PATH`;
4. `.env` at the project root.

For normal local use, copy `.env.example` to `.env` and provide the local
AutoCorrect2 path:

```dotenv
AUTOCORRECT2_PROJECT_DIR=H:/Projects/AutoCorrect2
```

The local `.env` file should remain untracked.

## Run the full pipeline

The following example reads source words from a UTF-8 file, creates the default
single-error and mixed two-error generation tasks, and checks the surviving
candidates against AutoCorrect2:

```powershell
uv run python -m hotstring full-pipeline `
    --words-file .\words.txt `
    --single-attempts 100 `
    --multi-attempts 100 `
    --multi-min-length 5 `
    --workers 4 `
    --report .\reports\full-pipeline.txt
```

AutoCorrect2-aware commands are read-only by default. Add `--write-accepted`
to append accepted candidates to `Core/GeneratedHotstrings.ahk`.

Logging verbosity is controlled by the repeatable top-level `-v` option, which
must appear before the subcommand:

```powershell
uv run python -m hotstring -v full-pipeline ...
uv run python -m hotstring -vv full-pipeline ...
```

`-v` enables informational logging, while `-vv` enables debug logging.

See the [command-line documentation](docs/command-line.md) for all arguments,
input formats, configuration sources, and exit statuses.

## Package architecture

The `hotstring` package separates generic AutoHotkey behavior,
AutoCorrect2-specific integration, typo generation, and the command-line
application layer:

<details open>
<summary><strong>Click to toggle</strong></summary>

```text
hotstring/
├── __init__.py
├── __main__.py
├── cli/
│   ├── __init__.py
│   ├── application.py
│   ├── commands.py
│   ├── parser.py
│   └── runtime.py
├── core/
│   ├── __init__.py
│   ├── constants.py
│   ├── conflicts.py
│   ├── models.py
│   ├── options.py
│   └── trigger.py
├── autocorrect2/
│   ├── __init__.py
│   ├── source_loading/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── loader.py
│   │   └── parser.py
│   ├── constants.py
│   ├── integration.py
│   ├── models.py
│   └── writer.py
├── typo_generation/
│   ├── __init__.py
│   ├── aggregation.py
│   ├── execution.py
│   ├── generation.py
│   └── models.py
├── constants.py
├── file_io.py
├── pipeline.py
└── report.py
```

</details>

`hotstring.core` is the generic AutoHotkey domain layer. It has no dependency
on AutoCorrect2 or typo generation.

`hotstring.autocorrect2` contains AutoCorrect2-specific source loading,
candidate rendering, integration management, and generated-file writing.

`hotstring.typo_generation` contains typo-generation models, execution, and
internal ambiguity filtering.

`hotstring.cli` is the application layer that parses command-line input,
resolves external configuration, constructs immutable runtime command objects,
and dispatches them to the public pipeline APIs.

Top-level `hotstring` modules are reserved for project-level orchestration,
reporting, and generic file I/O. The `hotstring.__main__` module provides the package entry point for
`python -m hotstring` and delegates execution to `hotstring.cli.application.main`.

## Trigger model

Hotstrings keep trigger meaning separate from AutoHotkey source spelling:

- `semantic_trigger` stores the actual characters AutoHotkey recognizes;
- `ahk_trigger` stores one deterministic, minimally escaped AutoHotkey source
  form;
- `case_insensitive_semantic_trigger_key` stores derived comparison state used
  by conflict detection.

The constructor-only `trigger` value is an `InitVar`. `Hotstring` and candidate
classes interpret it as semantic text by default. `ExistingHotstring` shadows
the class policy `TRIGGER_INPUT_IS_AHK_SOURCE = True`, so the same base
initialization algorithm decodes source-form input before deriving canonical
state.

Trigger conversion is intentionally asymmetric with respect to source spelling.
Multiple valid AutoHotkey spellings may decode to the same semantic trigger,
while `semantic_to_ahk_trigger()` always emits one canonical, minimally escaped
form.

When enabled, `CHECK_TRIGGER_ROUND_TRIP` verifies that the canonical AutoHotkey
form decodes back to the stored semantic trigger.

## Conflict detection

Conflict checking models hotstring recognition semantics rather than only
literal string equality. It supports combinations of the currently modeled
recognition options:

- `*` / `*0` — optional ending character;
- `?` / `?0` — inside-word matching;
- `C`, `C0`, `C1` — case matching.

The checker considers both activation directions, overlapping occurrences,
left and right boundaries, effective ending characters, and whether either
hotstring can match case-insensitively.

## AutoCorrect2 source loading

Existing AutoCorrect2 declarations are parsed with escape-aware trigger
scanning rather than a delimiter-only trigger regular expression.

The loader keeps parsing, persistent cache handling, and multi-file source
orchestration in separate modules under
`hotstring.autocorrect2.source_loading`.

The persistent cache stores only source-derived state needed for
reconstruction: canonical AutoHotkey trigger text and canonical option
declarations. SHA-256 of the exact source bytes is the authoritative content
identity.

Semantic trigger text and case-insensitive comparison keys are always rebuilt
from current code when cached data is restored.

## Generated candidates

The full pipeline converts surviving typo mappings to
`AutoCorrect2CandidateHotstring` objects using the generated `B0X` policy.

AutoCorrect2-specific rendering converts the semantic replacement to a safely
escaped AutoHotkey string literal and wraps it in `f(...)`.

Accepted entries can be appended to `Core/GeneratedHotstrings.ahk`. The writer
requires explicit `B0X` behavior, while generic conflict detection itself is
not restricted to those candidate options.

Add a one-time `#Include` for `Core/GeneratedHotstrings.ahk` in the same active
AutoCorrect2 hotstring context as the main autocorrection library. The generated
file is scanned on later runs when it exists.

## Documentation

Serve the documentation locally with:

```powershell
uv run mkdocs serve --strict
```

Build it with:

```powershell
uv run mkdocs build --strict
```

The documentation includes conceptual explanations, workflow guides,
configuration details, command-line usage, and a package-aligned API reference.

## Hosted site

The project documentation is hosted at:<br>
**[AutoCorrect2 Hotstring Generation](https://orfadida2000.github.io/autocorrect2-hotstring-generation)**

## License

MIT.<br>
See **[LICENSE](LICENSE)** for details.

## Author

- **Name:** Or Fadida
- **Email:** [or@fadida.net](mailto:or@fadida.net)
- **GitHub:** [orfadida2000](https://github.com/orfadida2000)
