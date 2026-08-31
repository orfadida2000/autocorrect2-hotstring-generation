# Workflows

Three public workflows are available:

1. typo generation only;
2. AutoCorrect2 checking only for manually supplied candidates;
3. the full composed workflow.

The full workflow reuses the first two rather than duplicating their logic.
Typo generation remains independent of AutoCorrect2; the adaptation from a
noisy-word mapping to `AutoCorrect2CandidateHotstring` belongs to the composed
pipeline.
