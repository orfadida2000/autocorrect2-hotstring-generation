# Conflict detection

Conflict checking operates on **effective** hotstring matching semantics, not
on whether a particular option token happened to be present in the source.

Before matching, a parsed `HotstringOptions` declaration is converted to a
`ResolvedHotstringOptions` using the defaults that apply at that declaration
position. Conflict detection then reads only the resolved fields it needs; it
does not maintain a separate matching-only options dataclass.

Conflict checking examines both directions:

1. whether an existing hotstring can activate while a candidate is typed;
2. whether the candidate can activate while an existing trigger is typed.

Left boundaries depend on whether an alphanumeric predecessor is permitted.
Right boundaries depend on `ending_character_optional` and, when an ending
character is required, the effective ending-character set.

Every occurrence is considered, including overlapping occurrences. Existing
case-sensitive hotstrings use exact-case occurrence matching; currently
supported case-insensitive candidates use case-insensitive matching.

The current candidate checker rejects only matching behaviors it does not yet
support for generated candidates, such as an effective optional ending
character (`*`), inside-word matching (`?`), or case-sensitive matching (`C`).
Unrelated options such as backspacing, execution, key delay, priority, send
mode, and recognizer reset do not gate conflict support.
