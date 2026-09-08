# AutoCorrect2 Hotstring Generation

This project generates plausible keyboard-typo hotstrings, removes ambiguous
generated mappings, checks the remaining candidates against AutoCorrect2, and
can append approved definitions to a dedicated generated AutoHotkey include
file.

The project deliberately separates three concerns:

- `hotstring.core` — generic AutoHotkey hotstring models, trigger conversion,
  option resolution, and conflict semantics;
- `hotstring.typo_generation` — typo generation and internal ambiguity
  filtering;
- `hotstring.autocorrect2` — AutoCorrect2-specific source loading, candidate
  rendering, integration checks, and generated-file writing.

Project-level orchestration, reporting, and generic file I/O remain at the
`hotstring` package root.

The processing stages can be used independently. Typo generation does not
depend on AutoCorrect2, and AutoCorrect2 checking can operate on manually
constructed candidates.
