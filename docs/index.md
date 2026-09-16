# AutoCorrect2 Hotstring Generation

This project generates plausible keyboard-typo hotstrings, removes ambiguous
generated mappings, checks the remaining candidates against AutoCorrect2, and
can append accepted definitions to a dedicated generated AutoHotkey include
file.

The project deliberately separates four concerns:

- `hotstring.core` — generic AutoHotkey hotstring models, trigger conversion,
  option resolution, and conflict semantics;
- `hotstring.typo_generation` — typo generation and internal ambiguity
  filtering;
- `hotstring.autocorrect2` — AutoCorrect2-specific source loading, candidate
  rendering, integration checks, and generated-file writing;
- `hotstring.cli` — command-line parsing, external-input resolution, runtime
  command construction, and pipeline dispatch.

Project-level orchestration, reporting, and generic file I/O remain at the
`hotstring` package root. The `hotstring.__main__` module provides the `python -m hotstring` entry point
and delegates command-line execution to `hotstring.cli.application.main`.

The processing stages can be used independently. Typo generation does not
depend on AutoCorrect2, and AutoCorrect2 checking can operate on manually
constructed candidates.

The three workflows are also available through the `typo-generation`,
`autocorrect2-check`, and `full-pipeline` subcommands.

**See also:** [Command-line interface](command-line.md) for command syntax and
shared runtime configuration.

**License:** This project is licensed under the [MIT License](license.md).
