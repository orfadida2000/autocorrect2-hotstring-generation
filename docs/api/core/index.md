# Core API

`hotstring.core` contains the generic AutoHotkey hotstring domain model and
recognition logic. It does not depend on AutoCorrect2 integration or typo
generation.

The subpackage contains:

- semantic/AHK trigger conversion and case-insensitive keys;
- hotstring and candidate domain models;
- option parsing and effective option resolution;
- conflict detection;
- generic AutoHotkey defaults and constants.
