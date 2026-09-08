# Hotstrings and options

## Trigger representations

The generic hotstring model keeps trigger **meaning** separate from AutoHotkey
source spelling.

Each initialized `Hotstring` stores two trigger representations:

- `semantic_trigger` — the actual characters AutoHotkey should recognize;
- `ahk_trigger` — the deterministic, minimally escaped spelling used when
  rendering AHK source.

The constructor argument `trigger` is an `InitVar`, so it is not retained as a
third ambiguous representation after initialization.

By default, `Hotstring` and candidate classes interpret constructor `trigger`
as semantic text. `ExistingHotstring` receives trigger text extracted from an
AHK source file, so it shadows the class policy
`TRIGGER_INPUT_IS_AHK_SOURCE = True`. The base `__post_init__()` still owns the
same resolution algorithm for every subclass:

```text
constructor trigger
        ↓ interpret according to class policy
semantic_trigger
        ↓ semantic_to_ahk_trigger(...)
ahk_trigger
```

When `CHECK_TRIGGER_ROUND_TRIP` is enabled, initialization also verifies the
conversion invariant:

```python
ahk_to_semantic_trigger(ahk_trigger) == semantic_trigger
```

This is an internal consistency check. A failure indicates a bug in the
conversion contract rather than invalid user input.

## Canonical AHK trigger spelling

`semantic_to_ahk_trigger()` produces one deterministic, minimally escaped AHK
representation.

Characters which always require source escaping, such as a literal backtick or
supported control characters, are escaped unconditionally. Colons and
semicolons are escaped only when their source context requires it:

- `:` is escaped only as needed to prevent an unescaped `::` sequence inside
  the trigger or against the declaration delimiter;
- `;` is escaped only when a literal source space immediately precedes it and
  it would otherwise begin a comment.

Consequently, multiple valid source spellings can decode to the same semantic
trigger. For example:

```text
foo:bar
foo`:bar
```

both decode to:

```text
foo:bar
```

and re-encode canonically as the minimally escaped form:

```text
foo:bar
```

The helpers are therefore intentionally asymmetric with respect to source
spelling. The supported semantic round trip is:

```python
ahk_to_semantic_trigger(semantic_to_ahk_trigger(value)) == value
```

for every semantic trigger accepted by the encoder. Re-encoding arbitrary AHK
source is allowed to canonicalize optional or unnecessary escapes.

## Case-insensitive matching key

Conflict detection operates on semantic trigger text, never on escaped AHK
source spelling. Each hotstring therefore caches a derived
`case_insensitive_semantic_trigger_key`.

On Windows the key is produced with the Microsoft CRT under an explicit C
locale to follow AutoHotkey's case-insensitive comparison basis as closely as
possible. On non-Windows systems, `str.lower()` is used as a deterministic
fallback. The key is runtime-derived state and is not persisted in the source
cache.

## Hotstring rendering

`Hotstring.render(content=None)` renders the canonical option declaration and
`ahk_trigger`, never the constructor input.

`content` means everything emitted after the declaration's second `::`. It is
therefore intentionally broader than an inline replacement RHS: depending on
AutoHotkey syntax and options, it may be replacement text, executable content,
or multiline block content.

The generic `Hotstring.to_ahk_string_literal()` helper separately handles AHK
double-quoted string syntax. It escapes literal backticks and quotes plus all
supported AHK control escapes (`r`, `n`, `b`, `t`, `v`, `a`, and `f`). Trigger
encoding and quoted-string encoding remain separate because their syntax rules
are different.

## Declared option state

`HotstringOptions` represents what is explicitly declared on one hotstring.
Every omitted option uses the shared sentinel:

```python
InheritedState.INHERIT
```

This is distinct from the actual semantic value of the option. For example,
`CaseMode` contains only real case modes, while inheritance is represented by
`InheritedState` rather than by a synthetic `CaseMode.INHERIT` member.

Two-state settings use `SettingState.ENABLED` and `SettingState.DISABLED`.
The `*` option is exposed semantically as `ending_character_optional`, so its
mapping is direct:

| Declaration | Semantic state           |
| ----------- | ------------------------ |
| `*`         | `SettingState.ENABLED`   |
| `*0`        | `SettingState.DISABLED`  |
| omitted     | `InheritedState.INHERIT` |

`declaration()` serializes the parsed semantic state back to one canonical
option string. Repeated or contradictory source options therefore collapse to
the last effective value rather than being reproduced verbatim.

## Resolved option state

`ResolvedHotstringOptions` is a separate dataclass rather than a subclass of
`HotstringOptions`. Its fields contain only concrete values; none are typed
with `InheritedState`.

`ResolvedHotstringOptions.from_options()` constructs a resolved object from:

1. one parsed `HotstringOptions` declaration; and
2. the fully resolved defaults applicable at that declaration position.

Explicit values override those defaults. `InheritedState.INHERIT` leaves the
corresponding default unchanged. This makes resolution context-sensitive
without making `HotstringOptions` itself aware of file position,
`#Hotstring`, or other sources of defaults.

## Send mode

The declared `SendMode` enum represents the three actual hotstring send-mode
choices:

```text
INPUT
PLAY
EVENT
```

The declaration mapping is:

| Hotstring option | Declared value           |
| ---------------- | ------------------------ |
| `SI`             | `SendMode.INPUT`         |
| `SP`             | `SendMode.PLAY`          |
| `SE`             | `SendMode.EVENT`         |
| omitted          | `InheritedState.INHERIT` |

Input mode has two distinct effective fallback behaviors, so the resolved model
uses a separate four-state enum:

```python
class ResolvedSendMode(Enum):
    INPUT_WITH_PLAY_FALLBACK = auto()
    INPUT_WITH_EVENT_FALLBACK = auto()
    PLAY = auto()
    EVENT = auto()
```

`ResolvedHotstringOptions.send_mode` is therefore typed as
`ResolvedSendMode`.

The important mappings are:

| Effective source            | Resolved value                               |
| --------------------------- | -------------------------------------------- |
| explicit `SI`               | `ResolvedSendMode.INPUT_WITH_PLAY_FALLBACK`  |
| AutoHotkey built-in default | `ResolvedSendMode.INPUT_WITH_EVENT_FALLBACK` |
| `SP`                        | `ResolvedSendMode.PLAY`                      |
| `SE`                        | `ResolvedSendMode.EVENT`                     |

`InheritedState.INHERIT` does not inherently mean
`INPUT_WITH_EVENT_FALLBACK`. It means to use the currently applicable hotstring
default. If inheritance eventually reaches AutoHotkey's untouched built-in
default, the resulting resolved value is
`ResolvedSendMode.INPUT_WITH_EVENT_FALLBACK`. If an applicable default has
already selected `SI`, `SP`, or `SE`, the inherited value resolves according
to that default instead.

## Candidate hierarchy

The generic model hierarchy is:

```text
Hotstring
    ↑
CandidateHotstring                (abstract)
    ↑
AutoCorrect2CandidateHotstring    (concrete)
```

`CandidateHotstring` stores the semantic `replacement` and requires a concrete
subclass to derive the AutoHotkey content corresponding to that replacement.
The generic public `render()` contract remains inherited from `Hotstring`, so
the hierarchy does not narrow the method signature.

`AutoCorrect2CandidateHotstring` supplies the AutoCorrect2-specific mapping:
the replacement is converted to a complete escaped AutoHotkey string literal
and wrapped in `f(...)`.
