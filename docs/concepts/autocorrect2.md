# AutoCorrect2 integration

The integration scans AutoCorrect2's known static hotstring sources plus the
project-owned generated include file when it exists.

Approved generated candidates are not inserted into
`AutoCorrectHotstrings.ahk`. Instead they are appended to
`Core/GeneratedHotstrings.ahk`, which AutoCorrect2 includes once through a
manually added `#Include` directive.

This keeps generated content separate from upstream-maintained source and
allows later conflict checks to see previously generated entries.
