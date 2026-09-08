# Hotstring options

This module contains the declared option model, inheritance sentinel, semantic
enums, and fully resolved option model.

The declared send mode uses `SendMode` (`INPUT`, `PLAY`, and `EVENT`). Fully
resolved options use the separate `ResolvedSendMode` enum so Input's Play and
Event fallback behaviors remain explicit without complicating the field type.

::: hotstring.core.options
