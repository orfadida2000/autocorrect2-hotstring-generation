# Conflict detection

Conflict checking examines both directions:

1. whether an existing hotstring can activate while a candidate is typed;
2. whether the candidate can activate while an existing trigger is typed.

Left boundaries depend on whether an alphanumeric predecessor is allowed.
Right boundaries depend on whether an ending character is required and on the
effective ending-character set.

Omitted matching options remain `None` in `HotstringOptions` and are resolved
separately against built-in defaults. The current candidate checker raises
`NotImplementedError` only for effective `*`, `?`, or case-sensitive `C`
matching. Unrelated options such as `B`, `X`, `O`, `K`, or `P` do not affect
conflict-check support.
