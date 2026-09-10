# Full pipeline

[`run_full_pipeline()`][hotstring.pipeline.run_full_pipeline] composes
[`run_typo_generation()`][hotstring.pipeline.run_typo_generation] with
[`run_autocorrect2_check()`][hotstring.pipeline.run_autocorrect2_check] and
returns a [`FullPipelineResult`][hotstring.pipeline.FullPipelineResult]:

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
