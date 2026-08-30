# Hotstrings and candidate models

`Hotstring` stores only trigger and options and can render an optional inline
RHS. `CandidateHotstring` is abstract: a concrete subclass owns the mapping
from semantic replacement text to an AHK RHS and caches that RHS at
initialization.

`AutoCorrect2CandidateHotstring` implements the concrete AutoCorrect2 rule:
the replacement is converted to an escaped AHK string literal and wrapped in
`f(...)`.

The generic `Hotstring.to_ahk_string_literal()` helper owns AHK string-literal
escaping because that logic is not AutoCorrect2-specific.
