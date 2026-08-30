# Typo-generation configuration

`TypoGenerationConfig` contains generation semantics:

- `generation_attempts_per_word`;
- ordered typo distributions;
- MULTYPO language;
- excluding-set behavior;
- horizontal-vs-vertical keyboard-neighbor weights.

`n_workers` is deliberately a pipeline/execution argument rather than part of
the semantic configuration, because worker count changes how work is executed
rather than what generation was requested.
