# Full pipeline

```text
source words
        ↓
run_typo_generation(...)
        ↓
TypoGenerationResult.candidates
        ↓
adapt noisy -> target mappings to AutoCorrect2CandidateHotstring
        ↓
run_autocorrect2_check(...)
        ↓
FullPipelineResult
```

The adaptation step is where the generated AutoCorrect2 candidate option policy
is applied. Typo generation itself has no dependency on
[`HotstringOptions`][hotstring.core.options.HotstringOptions] or AutoCorrect2.

The full pipeline disables stage-specific report writing while composing the
two stages and creates one combined report at the end when requested.
