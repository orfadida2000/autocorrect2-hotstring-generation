# Full pipeline

[`run_full_pipeline()`][hotstring.pipeline.run_full_pipeline] composes
[`run_typo_generation()`][hotstring.pipeline.run_typo_generation] with
[`run_autocorrect2_check()`][hotstring.pipeline.run_autocorrect2_check] and
returns a [`FullPipelineResult`][hotstring.pipeline.FullPipelineResult]:

???+ info "Full Pipeline Workflow"

    ```mermaid
    flowchart TD
        A["Source words and<br>generation settings"] --> B["Generate typo<br>mappings"]
        B --> C["TypoGenerationResult"]
        C -->|"candidate mappings"| D["Create B0X<br>AutoCorrect2 candidates"]
        D --> E["Check against<br>AutoCorrect2"]
        E --> F["AutoCorrect2CheckResult"]
        C --> G["FullPipelineResult"]
        F --> G
    ```

The adaptation step converts each surviving noisy-to-target mapping into an
[`AutoCorrect2CandidateHotstring`][hotstring.autocorrect2.models.AutoCorrect2CandidateHotstring]
using the fixed generated option set `B0X`. Typo generation itself has no
dependency on
[`HotstringOptions`][hotstring.core.options.HotstringOptions] or AutoCorrect2.

The full pipeline disables stage-specific report writing while composing the
two stages and creates one combined report at the end when requested.

## Command-line usage

Run the composed workflow with `full-pipeline`:

```powershell
uv run python -m hotstring full-pipeline `
    --words-file .\words.txt `
    --single-attempts 100 `
    --multi-attempts 100 `
    --multi-min-length 5 `
    --workers 4 `
    --report .\reports\full-pipeline.txt
```

The AutoCorrect2 project directory is resolved from `--project-dir`, the
process environment, an explicit dotenv file, or the project-root `.env`.

The command remains read-only unless `--write-accepted` is supplied. It does
not accept manually supplied candidates because it creates `B0X` candidates
from the typo-generation result.

**See also:** [Command-line interface](../command-line.md) for all shared options.
