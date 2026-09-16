# Workflows

Three public workflows are available through both Python APIs and matching CLI
subcommands:

1. standalone typo generation through
   [`run_typo_generation()`][hotstring.pipeline.run_typo_generation] and
   `typo-generation` respectively;
2. standalone AutoCorrect2 conflict checking through
   [`run_autocorrect2_check()`][hotstring.pipeline.run_autocorrect2_check] and
   `autocorrect2-check` respectively;
3. the composed workflow through
   [`run_full_pipeline()`][hotstring.pipeline.run_full_pipeline] and
   `full-pipeline` respectively.

The full workflow reuses the first two rather than duplicating their logic.
Typo generation remains independent of AutoCorrect2; the adaptation from a
noisy-word mapping to
[`AutoCorrect2CandidateHotstring`][hotstring.autocorrect2.models.AutoCorrect2CandidateHotstring]
belongs to the composed pipeline.

**See also:** [Command-line interface](../command-line.md) for command syntax and shared
runtime configuration.
