# AutoCorrect2 configuration

## Project directory

The project does not contain a hard-coded local AutoCorrect2 path. The CLI
resolves the directory in this order:

1. `--project-dir PATH`;
2. the process environment variable `AUTOCORRECT2_PROJECT_DIR`;
3. the dotenv file selected by `--env-file PATH`;
4. `.env` at the project root.

Resolution stops at the first configured source. Relative values from a dotenv
file are resolved relative to that file's directory. Relative command-line and
process-environment values are resolved relative to the current working
directory.

A dotenv file uses:

```dotenv
AUTOCORRECT2_PROJECT_DIR=H:/Projects/AutoCorrect2
```

## Required sources

The selected AutoCorrect2 project directory must contain:

- `Core/AutoCorrectHotstrings.ahk`
- `Core/PersonalHotstrings.ahk`
- `Includes/DateTool.ahk`

`Core/GeneratedHotstrings.ahk` is optional on the first run and is scanned once
it exists.

## Generated output

AutoCorrect2-aware commands are read-only by default. `--write-accepted`
enables appending accepted candidates to `Core/GeneratedHotstrings.ahk`.

Candidates supplied manually to `autocorrect2-check` must satisfy the writer's
explicit generated-option contract before they can be written. The full
pipeline creates generated candidates with the required `B0X` options.

## Matching defaults

[`HotstringOptions`][hotstring.core.options.HotstringOptions] does not bake
AutoHotkey defaults into omitted fields. Omitted values remain the `INHERIT`
member of [`InheritedState`][hotstring.core.options.InheritedState] until a
[`ResolvedHotstringOptions`][hotstring.core.options.ResolvedHotstringOptions] is
created with the defaults that apply at that source position.

Resolution combines the parsed declaration with the fully resolved defaults
applicable at that source position:

???+ info "Resolution Diagram"

    ```mermaid
    flowchart TD
        A["HotstringOptions<br>declaration"] --> C["Resolve inherited<br>fields"]
        B["Applicable<br>resolved defaults"] --> C
        C --> D["ResolvedHotstringOptions<br>effective state"]
    ```

Until positional directive analysis is implemented, the AutoCorrect2 pipeline
can resolve declarations against the configured built-in/default option object.

The conflict checker currently assumes the configured ending-character set and
uses only the resolved recognition-related fields required for matching.
