# Typo-generation configuration

`TypoGenerationConfig` contains generation semantics:

- `generation_attempts_per_word`;
- ordered typo distributions;
- MULTYPO language;
- excluding-set behavior;
- horizontal-vs-vertical keyboard-neighbor weights.

Distribution labels are intentionally not part of the public model. The actual
`TypoDistribution` objects are the configuration that matters.

`n_workers` is deliberately a pipeline/execution argument rather than part of
the semantic configuration because worker count changes how work is executed,
not what typo generation was requested.
