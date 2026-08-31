# AutoCorrect2 Hotstring Generation

This project generates plausible keyboard-typo hotstrings, removes ambiguous
generated mappings, checks the remaining candidates against AutoCorrect2, and
can append approved definitions to a dedicated generated AutoHotkey include
file.

The project deliberately separates three concerns:

- generic AutoHotkey hotstring parsing, rendering, option resolution, and conflict semantics;
- typo generation and internal ambiguity filtering;
- AutoCorrect2-specific parsing, candidate rendering, and output writing.

The two processing stages can be used independently. Typo generation does not
depend on AutoCorrect2, and AutoCorrect2 checking can operate on manually
constructed candidates.
