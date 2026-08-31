# Concepts

The project separates generic AutoHotkey semantics, typo sampling,
AutoCorrect2 integration, and orchestration.

The main conceptual boundaries are:

- **declared vs resolved hotstring options**;
- **generic hotstrings vs semantic correction candidates**;
- **generic candidates vs AutoCorrect2-specific candidates**;
- **typo generation vs AutoCorrect2 conflict checking**;
- **report construction vs filesystem output**.

These boundaries allow either processing stage to run independently and keep
context-dependent AutoHotkey defaults out of the parser itself.
