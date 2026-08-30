# AutoCorrect2 Hotstring Generation

Generate keyboard-typo candidates with MULTYPO, remove internally ambiguous
mappings, validate the remaining candidates against active AutoCorrect2
hotstrings, and optionally append accepted entries to a dedicated generated
AutoHotkey include file.

The package exposes three independent workflows:

1. typo generation only;
2. AutoCorrect2 conflict checking only for manually supplied candidates;
3. the full composed workflow.

See the MkDocs documentation in `docs/` for architecture, configuration,
workflow, and API details.
