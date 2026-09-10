# Workflows

Three public workflows are available:

1. standalone typo generation;
2. standalone AutoCorrect2 conflict checking for supplied candidates;
3. the full pipeline, which composes the first two.

The full workflow reuses the first two rather than duplicating their logic.
Typo generation remains independent of AutoCorrect2; the adaptation from a
noisy-word mapping to
[`AutoCorrect2CandidateHotstring`][hotstring.autocorrect2.models.AutoCorrect2CandidateHotstring]
belongs to the composed pipeline.
