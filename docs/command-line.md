# Command-line usage

The `hotstring.__main__` module provides the `python -m hotstring` entry point and delegates
command-line execution to [`main()`][hotstring.cli.application.main] which exposes the project's three
public workflows as subcommands.

| Subcommand           | Workflow                                                              |
| -------------------- | --------------------------------------------------------------------- |
| `typo-generation`    | Generate typo mappings and remove internally ambiguous mappings       |
| `autocorrect2-check` | Check supplied candidates against existing AutoCorrect2 hotstrings    |
| `full-pipeline`      | Generate typo candidates and check the survivors against AutoCorrect2 |

Display the top-level help or the help for one subcommand with:

```powershell
uv run python -m hotstring --help
uv run python -m hotstring typo-generation --help
uv run python -m hotstring autocorrect2-check --help
uv run python -m hotstring full-pipeline --help
```

## Logging verbosity

`-v` and `--verbose` are repeatable top-level options:

| Invocation          | Logging level                                                          |
| ------------------- | ---------------------------------------------------------------------- |
| no verbosity option | Normal command summaries and concise errors                            |
| `-v`                | Informational logging                                                  |
| `-vv`               | Debug logging, including a traceback for an unexpected runtime failure |

The verbosity option belongs to the top-level parser, so it must appear before
the subcommand:

```powershell
uv run python -m hotstring -v typo-generation ...
uv run python -m hotstring -vv full-pipeline ...
```

Repeating `-v` more than twice continues to use debug logging.

## Typo generation

`typo-generation` requires exactly one source of words:

- repeat `--word WORD` to supply words directly; or
- use `--words-file PATH` for a UTF-8 file containing one word per line.

Blank lines are ignored, and duplicate words are removed while preserving
their first occurrence.

The command creates the project's default ordered
[`TypoGenerationTask`][hotstring.typo_generation.models.TypoGenerationTask]
sequence from these required arguments:

| Argument                    | Meaning                                                      |
| --------------------------- | ------------------------------------------------------------ |
| `--single-attempts COUNT`   | Attempts per eligible word for each forced single-error task |
| `--multi-attempts COUNT`    | Attempts per eligible word for the mixed two-error task      |
| `--multi-min-length LENGTH` | Minimum word length for the mixed two-error task             |

Optional generation arguments are:

| Argument                                 | Meaning                                                                |
| ---------------------------------------- | ---------------------------------------------------------------------- |
| `--language LANGUAGE`                    | MULTYPO language identifier; defaults to `english`                     |
| `--excluding-set` / `--no-excluding-set` | Enable or disable MULTYPO's language excluding set; enabled by default |
| `--keyboard-weights HORIZONTAL VERTICAL` | Relative keyboard-neighbor weights; defaults to `9 1`                  |
| `--workers COUNT`                        | Process-pool size; omit it to use the execution layer's default        |
| `--report PATH`                          | Write a typo-generation report                                         |

For example:

```powershell
uv run python -m hotstring typo-generation `
    --words-file .\words.txt `
    --single-attempts 100 `
    --multi-attempts 100 `
    --multi-min-length 5 `
    --workers 4 `
    --report .\reports\typo-generation.txt
```

This subcommand does not load or modify an AutoCorrect2 project.

## AutoCorrect2 project directory

The `autocorrect2-check` and `full-pipeline` subcommands resolve the local
AutoCorrect2 project directory in this order:

1. `--project-dir PATH`;
2. the process environment variable `AUTOCORRECT2_PROJECT_DIR`;
3. the dotenv file selected by `--env-file PATH`;
4. `.env` at the project root.

Resolution stops at the first configured source. A lower-priority dotenv file
is therefore not opened or validated after a command-line or process-environment
value has been selected.

A project-root `.env` file can contain:

```dotenv
AUTOCORRECT2_PROJECT_DIR=H:/Projects/AutoCorrect2
```

An explicit dotenv file uses the same key:

```powershell
uv run python -m hotstring autocorrect2-check `
    --env-file .\config\autocorrect2.env `
    --candidate "teh" "the" "B0X"
```

A relative value read from a dotenv file is resolved relative to that file's
directory. A relative `--project-dir` value or process-environment value is
resolved relative to the current working directory.

See [AutoCorrect2 configuration](configuration/autocorrect2.md) for the
required source-file layout and generated-file policy.

## AutoCorrect2 conflict checking

`autocorrect2-check` accepts manually supplied
[`AutoCorrect2CandidateHotstring`][hotstring.autocorrect2.models.AutoCorrect2CandidateHotstring]
objects without running typo generation.

Supply candidates directly by repeating `--candidate` with three values:

```text
--candidate TRIGGER REPLACEMENT OPTIONS
```

For example:

```powershell
uv run python -m hotstring autocorrect2-check `
    --candidate "teh" "the" "B0X" `
    --candidate "adn" "and" "B0X" `
    --project-dir "H:\Projects\AutoCorrect2" `
    --report .\reports\autocorrect2-check.txt
```

Alternatively, `--candidates-file PATH` accepts a UTF-8 JSON file containing a
top-level array. Every object must contain exactly the string fields `trigger`,
`replacement`, and `options`:

```json
[
  {
    "trigger": "teh",
    "replacement": "the",
    "options": "B0X"
  },
  {
    "trigger": "adn",
    "replacement": "and",
    "options": "B0X"
  }
]
```

Use the file with:

```powershell
uv run python -m hotstring autocorrect2-check `
    --candidates-file .\candidates.json
```

`--candidate` and `--candidates-file` are mutually exclusive.

## Full pipeline

`full-pipeline` composes typo generation and AutoCorrect2 conflict checking.
It accepts the same word and generation arguments as `typo-generation`, then
converts the surviving mappings into generated `B0X` candidates before running
the AutoCorrect2 check.

For example:

```powershell
uv run python -m hotstring full-pipeline `
    --words-file .\words.txt `
    --single-attempts 100 `
    --multi-attempts 100 `
    --multi-min-length 5 `
    --workers 4 `
    --report .\reports\full-pipeline.txt
```

The project directory can come from any of the four configuration sources
described above. `full-pipeline` does not accept `--candidate` or
`--candidates-file`, because it creates candidates from the typo-generation
result.

## Reports and generated output

All three subcommands accept `--report PATH`. Parent directories are created by
the reporting layer when required.

AutoCorrect2-aware commands are read-only by default. Supply
`--write-accepted` to append accepted candidates to
`Core/GeneratedHotstrings.ahk`:

```powershell
uv run python -m hotstring full-pipeline `
    --words-file .\words.txt `
    --single-attempts 100 `
    --multi-attempts 100 `
    --multi-min-length 5 `
    --write-accepted
```

Writing manually supplied candidates remains subject to the writer's explicit
generated-option contract.

## Exit statuses

| Status | Meaning                                                           |
| ------ | ----------------------------------------------------------------- |
| `0`    | The selected workflow completed successfully                      |
| `1`    | Pipeline execution failed                                         |
| `2`    | Command-line syntax or resolved runtime configuration was invalid |
| `130`  | Execution was interrupted from the terminal                       |
