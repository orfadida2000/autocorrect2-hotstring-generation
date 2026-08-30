# Typo generation

Each source item is treated as exactly one word. For every configured typo
distribution and every source word, MULTYPO is sampled
`generation_attempts_per_word` times.

MULTYPO itself always receives `typo_rate=1.0`, because every sampling attempt
is intended to corrupt the one supplied word. The project therefore does not
expose its old custom `typo_rate` scaling argument.

The low-level generator uses `insert_typos()` directly rather than the
sentence-oriented `insert_typos_in_text()` wrapper, so sentence tokenization
and NLTK resources are unnecessary for this workflow.
