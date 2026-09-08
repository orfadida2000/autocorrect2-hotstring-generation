# Conflict detection

Conflict checking operates on **semantic trigger text** and **effective
hotstring matching semantics**, not on AHK source spelling or on whether a
particular option token happened to be present in the source.

Before matching, a parsed `HotstringOptions` declaration is converted to a
`ResolvedHotstringOptions` using the defaults that apply at that declaration
position. Conflict detection then reads only the resolved recognition fields it
needs.

## Matching directions

Conflict checking examines both directions:

1. whether an existing hotstring can activate while a candidate is typed;
2. whether the candidate can activate while an existing trigger is typed.

Every occurrence is considered, including overlapping occurrences. The
implementation uses repeated `str.find()` searches advancing by one character,
so a trigger such as `ana` is found at both valid positions in `banana`.

## Recognition options

The checker supports all combinations of the recognition-related hotstring
options currently modeled by the project:

- `*` / `*0` — whether an ending character is optional;
- `?` / `?0` — whether an alphanumeric predecessor is permitted;
- `C`, `C0`, and `C1` — effective case matching.

Options unrelated to trigger recognition, such as backspacing, execution,
priority, send mode, replacement mode, key delay, or recognizer reset, do not
affect conflict recognition.

## Boundaries

A matching occurrence has a valid left boundary when one of these is true:

- the occurrence starts at the beginning of the containing trigger;
- the preceding character is non-alphanumeric;
- the tested hotstring permits an alphanumeric predecessor through `?`.

The right boundary is valid when one of these is true:

- the tested hotstring does not require an ending character (`*` is enabled);
- the occurrence reaches the end of the containing trigger, because a later
  typed ending character can still activate it;
- the following character is in the effective ending-character set.

An ending character may itself appear anywhere inside a hotstring trigger. That
is valid AutoHotkey input; the character matters to conflict logic only when it
serves as the character immediately following a shorter matched occurrence.

## Case matching

If both compared hotstrings are case-sensitive, occurrence and same-trigger
checks use their exact `semantic_trigger` strings.

If either hotstring is case-insensitive, a shared typed casing can exist when
their AutoHotkey-compatible case-insensitive semantic keys match. The cached
`case_insensitive_semantic_trigger_key` is derived once from each semantic
trigger and reused throughout matching.

On Windows the key uses the Microsoft CRT C-locale lowercase basis. The
non-Windows fallback uses `str.lower()` and includes a defensive slice-based
path if lowercasing changes string length.
