# AutoCorrect2 integration

The AutoCorrect2 layer owns only behavior that is specific to the external
AutoCorrect2 project.

The parser scans the configured static hotstring sources plus the project-owned
generated include file when it exists. Parsed declarations use the generic
`HotstringOptions` model; their effective values can be resolved against the
defaults applicable at their source position.

Approved generated candidates are represented by
`AutoCorrect2CandidateHotstring`. Its concrete replacement-to-content mapping
wraps a safely escaped AutoHotkey string literal in AutoCorrect2's `f(...)`
helper.

Generated candidates are not inserted into upstream-maintained
`AutoCorrectHotstrings.ahk`. They are appended to
`Core/GeneratedHotstrings.ahk`, which AutoCorrect2 includes once through a
manually added `#Include` directive.

Keeping generated content separate allows later conflict checks to inspect
previously generated entries without modifying upstream-maintained files.
