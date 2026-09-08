# AutoCorrect2 integration

The AutoCorrect2 layer owns only behavior that is specific to the external
AutoCorrect2 project.

## Source loading

Existing declarations are loaded through the nested
`hotstring.autocorrect2.source_loading` package:

- `parser` extracts static hotstring declarations from decoded source text;
- `cache` persists source fingerprints and minimal extracted state;
- `loader` coordinates the configured required and optional source files.

The parser is escape-aware. It scans trigger source character by character so
escaped colons and backticks cannot be mistaken for the trigger's closing `::`
delimiter.

Parsed trigger text is supplied to `ExistingHotstring` in AHK source form. The
generic model then derives `semantic_trigger`, canonical `ahk_trigger`, parsed
options, and the case-insensitive semantic comparison key.

The persistent source cache stores canonical AHK trigger text and canonical
option declarations, not semantic or comparison-key state. SHA-256 of the exact
source bytes is authoritative for content identity; size and modification time
are metadata only. Cached semantic state is rebuilt by the current model every
time an entry is restored.

## Candidate rendering and output

Approved generated candidates are represented by
`AutoCorrect2CandidateHotstring`. Its concrete replacement-to-content mapping
wraps a safely escaped AutoHotkey string literal in AutoCorrect2's `f(...)`
helper.

Generated candidates are not inserted into upstream-maintained
`AutoCorrectHotstrings.ahk`. They are appended to
`Core/GeneratedHotstrings.ahk`, which AutoCorrect2 includes once through a
manually added `#Include` directive.

The writer enforces the generated-file `B0X` contract. Generic conflict
detection is deliberately independent of that output policy and supports other
recognition-option combinations.

Keeping generated content separate allows later conflict checks to inspect
previously generated entries without modifying upstream-maintained files.
