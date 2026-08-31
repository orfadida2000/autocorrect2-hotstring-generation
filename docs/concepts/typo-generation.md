# Typo generation

Each source item is treated as exactly one word. For every configured typo
distribution and every source word, MULTYPO is sampled
`generation_attempts_per_word` times.

MULTYPO itself receives `typo_rate=1.0` for each attempt because every sampling
attempt is intended to corrupt the supplied word. The project therefore does
not expose the old custom `typo_rate` argument that previously scaled the
number of iterations.

The low-level generator uses `insert_typos()` directly rather than the
sentence-oriented `insert_typos_in_text()` wrapper. Sentence tokenization and
NLTK resources are therefore unnecessary for this workflow.

Raw samples are aggregated by noisy form. A noisy form that maps to exactly
one target word becomes a candidate; one that maps to multiple target words is
recorded as an internal clash and removed before AutoCorrect2 processing.
