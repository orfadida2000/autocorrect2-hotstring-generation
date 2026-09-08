# Trigger representations

This module owns conversion between semantic trigger text and deterministic,
minimally escaped AutoHotkey source spelling, plus the reusable
case-insensitive comparison key derived from semantic text.

The semantic-to-AHK and AHK-to-semantic helpers are intentionally asymmetric
with respect to source spelling: multiple valid AHK spellings can normalize to
one canonical source representation.

::: hotstring.core.trigger
