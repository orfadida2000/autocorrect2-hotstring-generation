# Core models

This module contains the generic `Hotstring` model, the abstract
`CandidateHotstring` specialization, and `ExistingHotstring` for declarations
loaded from AHK source.

`Hotstring` uses a class-level trigger-input policy rather than subclass
resolver methods. `ExistingHotstring` shadows that policy so the shared base
initialization logic knows its constructor trigger is AHK source text.

::: hotstring.core.models
