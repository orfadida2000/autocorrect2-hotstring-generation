# Full pipeline

```text
source words
        ↓
run_typo_generation(...)
        ↓
TypoGenerationResult.candidates
        ↓
normalize to AutoCorrect2CandidateHotstring with B0X
        ↓
run_autocorrect2_check(...)
        ↓
FullPipelineResult
```

The full pipeline disables stage-specific report writing while composing the
two stages and creates one combined report at the end when requested.
