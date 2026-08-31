# Typo generation only

```text
source words
  + TypoGenerationConfig
  + n_workers execution option
        ↓
raw MULTYPO samples
        ↓
aggregation and internal ambiguity filtering
        ↓
TypoGenerationResult
```

`TypoGenerationResult.candidates` maps each unambiguous noisy form to exactly
one target word. `clashes` contains noisy forms that mapped to multiple target
words and are therefore removed before any AutoCorrect2 processing.

This workflow has no dependency on AutoCorrect2 hotstring models or option
policies.
