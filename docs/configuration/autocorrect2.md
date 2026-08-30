# AutoCorrect2 configuration

The default integration expects these required hotstring sources:

- `Core/AutoCorrectHotstrings.ahk`
- `Core/PersonalHotstrings.ahk`
- `Includes/DateTool.ahk`

`Core/GeneratedHotstrings.ahk` is optional on the first run and is scanned
automatically once it exists.

The current conflict checker assumes AutoHotkey's built-in ending characters
and built-in matching defaults unless a caller explicitly supplies different
effective values. Positional `#Hotstring` directive analysis can be added
later without changing `HotstringOptions` itself.
