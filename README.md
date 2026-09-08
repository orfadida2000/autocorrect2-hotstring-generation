# AutoCorrect2 Hotstring Generation

Generate plausible keyboard-typo hotstrings with MULTYPO, remove internally
ambiguous mappings, validate the remaining candidates against active
AutoCorrect2 hotstrings, and optionally append accepted entries to a dedicated
generated AutoHotkey include file.

The project exposes three independent workflows:

1. typo generation only;
2. AutoCorrect2 conflict checking only for manually supplied candidates;
3. the full composed workflow.

## Architecture

The source tree separates generic AutoHotkey hotstring behavior from
AutoCorrect2-specific integration and typo generation:

```text
hotstring/
├── core/
│   ├── constants.py
│   ├── conflicts.py
│   ├── models.py
│   ├── options.py
│   └── trigger.py
├── autocorrect2/
│   ├── source_loading/
│   │   ├── cache.py
│   │   ├── loader.py
│   │   └── parser.py
│   ├── constants.py
│   ├── integration.py
│   ├── models.py
│   └── writer.py
├── typo_generation/
│   ├── aggregation.py
│   ├── execution.py
│   ├── generation.py
│   └── models.py
├── constants.py
├── file_io.py
├── pipeline.py
└── report.py
```

`hotstring.core` is the generic AutoHotkey domain layer. It has no dependency
on AutoCorrect2 or typo generation. Top-level `hotstring` modules are reserved
for project-level orchestration, reporting, and generic file I/O.

## Trigger model

Hotstrings keep trigger meaning separate from AHK source spelling:

- `semantic_trigger` stores the actual characters AutoHotkey recognizes;
- `ahk_trigger` stores one deterministic, minimally escaped AHK source form;
- `case_insensitive_semantic_trigger_key` stores derived comparison state used
  by conflict detection.

The constructor-only `trigger` value is an `InitVar`. `Hotstring` and candidate
classes interpret it as semantic text by default. `ExistingHotstring` shadows
the class policy `TRIGGER_INPUT_IS_AHK_SOURCE = True`, so the same base
initialization algorithm decodes source-form input before deriving canonical
state.

Trigger conversion is intentionally asymmetric with respect to source spelling:
multiple valid AHK spellings may decode to the same semantic trigger, while
`semantic_to_ahk_trigger()` always emits one canonical minimally escaped form.
When enabled, `CHECK_TRIGGER_ROUND_TRIP` verifies that the canonical AHK form
decodes back to the stored semantic trigger.

## Conflict detection

Conflict checking models recognition semantics rather than only literal string
equality. It supports all combinations of the currently modeled recognition
options:

- `*` / `*0` — optional ending character;
- `?` / `?0` — inside-word matching;
- `C`, `C0`, `C1` — case matching.

The checker considers both activation directions, overlapping occurrences,
left and right boundaries, effective ending characters, and whether either
hotstring can match case-insensitively.

## AutoCorrect2 source loading

Existing AutoCorrect2 declarations are parsed with escape-aware trigger
scanning rather than a delimiter-only trigger regex. The loader keeps parsing,
persistent cache handling, and multi-file source orchestration in separate
modules under `hotstring.autocorrect2.source_loading`.

The persistent cache stores only source-derived state needed for reconstruction:
canonical AHK trigger text and canonical option declarations. SHA-256 of the
exact source bytes is the authoritative content identity. Semantic trigger text
and case-insensitive keys are always rebuilt from current code when cache data
is restored.

## Generated candidates

The full pipeline converts surviving typo mappings to
`AutoCorrect2CandidateHotstring` objects using the generated `B0X` policy.
AutoCorrect2-specific rendering wraps a safely escaped AHK string literal in
`f(...)`.

Accepted entries can be appended to `Core/GeneratedHotstrings.ahk`. The writer
requires explicit `B0X` behavior, while generic conflict detection itself is
not restricted to those candidate options.

## Development

The project targets Python 3.12+ and uses `uv` as a non-package project.

```powershell
uv sync
```

Build or serve the documentation with:

```powershell
uv run mkdocs serve
```

The MkDocs configuration references custom stylesheet files under
`docs/assets/stylesheets/`.

See the MkDocs documentation in `docs/` for architecture, configuration,
workflows, and the package-aligned API reference.
