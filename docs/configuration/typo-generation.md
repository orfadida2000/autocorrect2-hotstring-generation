# Typo-generation configuration

[`TypoGenerationConfig`][hotstring.typo_generation.models.TypoGenerationConfig]
contains settings shared by every task in one generation run:

- `language`;
- `use_excluding_set`;
- `horizontal_vs_vertical`.

Individual sampling policies are represented by
[`TypoGenerationTask`][hotstring.typo_generation.models.TypoGenerationTask].
Each task defines:

- its typo-operation distribution;
- its typo rate;
- its generation attempts per eligible word;
- its minimum eligible word length.

## Default CLI task set

The CLI uses
[`create_default_typo_generation_tasks()`][hotstring.typo_generation.models.create_default_typo_generation_tasks]
to construct the ordered default task sequence:

- one forced single-error task for each supported operation distribution;
- one mixed two-error task.

The required CLI arguments are:

| Argument                    | Runtime setting                                     |
| --------------------------- | --------------------------------------------------- |
| `--single-attempts COUNT`   | Attempts per word for each forced single-error task |
| `--multi-attempts COUNT`    | Attempts per word for the mixed two-error task      |
| `--multi-min-length LENGTH` | Minimum word length for the mixed two-error task    |

Shared generator settings use:

| Argument                                 | Runtime setting                               |
| ---------------------------------------- | --------------------------------------------- |
| `--language LANGUAGE`                    | `TypoGenerationConfig.language`               |
| `--excluding-set` / `--no-excluding-set` | `TypoGenerationConfig.use_excluding_set`      |
| `--keyboard-weights HORIZONTAL VERTICAL` | `TypoGenerationConfig.horizontal_vs_vertical` |

## Execution setting

`--workers COUNT` becomes the pipeline's `n_workers` argument. Worker count is
not part of `TypoGenerationConfig` because it changes how the requested work is
executed, not the requested generation semantics.
