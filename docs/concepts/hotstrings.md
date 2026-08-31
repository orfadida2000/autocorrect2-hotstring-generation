# Hotstrings and options

## Hotstring model

`Hotstring` stores a trigger and a `HotstringOptions` object. Its
`render(content=None)` method renders the canonical option declaration rather
than reusing the raw input option string.

`content` means everything emitted after the declaration's second `::`. It is
therefore intentionally broader than an inline replacement RHS: depending on
AutoHotkey syntax and options, it may be replacement text, executable content,
or multiline block content.

The renderer does not reject `\n` or `\r`, because valid AutoHotkey hotstrings
can use multiline bodies.

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

| Declaration | Semantic state |
| --- | --- |
| `*` | `SettingState.ENABLED` |
| `*0` | `SettingState.DISABLED` |
| omitted | `InheritedState.INHERIT` |

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

| Hotstring option | Declared value |
| --- | --- |
| `SI` | `SendMode.INPUT` |
| `SP` | `SendMode.PLAY` |
| `SE` | `SendMode.EVENT` |
| omitted | `InheritedState.INHERIT` |

Input mode has two distinct effective fallback behaviors, so the resolved model
uses a separate four-state enum:

```python
class ResolvedSendMode(Enum):
    INPUT_WITH_PLAY_FALLBACK = auto()
    INPUT_WITH_EVENT_FALLBACK = auto()
    PLAY = auto()
    EVENT = auto()
```

`ResolvedHotstringOptions.send_mode` is therefore simply typed as
`ResolvedSendMode`.

The important mappings are:

| Effective source | Resolved value |
| --- | --- |
| explicit `SI` | `ResolvedSendMode.INPUT_WITH_PLAY_FALLBACK` |
| AutoHotkey built-in default | `ResolvedSendMode.INPUT_WITH_EVENT_FALLBACK` |
| `SP` | `ResolvedSendMode.PLAY` |
| `SE` | `ResolvedSendMode.EVENT` |

`InheritedState.INHERIT` does not inherently mean
`INPUT_WITH_EVENT_FALLBACK`. It means to use the currently applicable hotstring
default. If inheritance eventually reaches AutoHotkey's untouched built-in
default, the resulting resolved value is
`ResolvedSendMode.INPUT_WITH_EVENT_FALLBACK`. If an applicable default has
already selected `SI`, `SP`, or `SE`, the inherited value resolves according
to that default instead.

This separation keeps `SendMode` aligned with the three declarable AHK modes
while allowing `ResolvedHotstringOptions` to represent the four effective
runtime behaviors without tuple or union-based fallback encoding.

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

`Hotstring.to_ahk_string_literal()` remains generic because AutoHotkey string
literal escaping is not AutoCorrect2-specific.
