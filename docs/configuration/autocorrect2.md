# AutoCorrect2 configuration

The default integration expects these required hotstring sources:

- `Core/AutoCorrectHotstrings.ahk`
- `Core/PersonalHotstrings.ahk`
- `Includes/DateTool.ahk`

`Core/GeneratedHotstrings.ahk` is optional on the first run and is scanned once
it exists.

## Matching defaults

`HotstringOptions` does not bake AutoHotkey defaults into omitted fields.
Omitted values remain `InheritedState.INHERIT` until a
`ResolvedHotstringOptions` is created with the defaults that apply at that
source position.

This design supports multiple default sources cleanly:

```text
per-hotstring declaration
        ↓ inherit
positional/default context such as #Hotstring
        ↓
fully resolved effective state
```

Until positional directive analysis is implemented, the AutoCorrect2 pipeline
can resolve declarations against the configured built-in/default option object.

The conflict checker currently assumes the configured ending-character set and
uses only the resolved recognition-related fields required for matching.
