# AutoCorrect2 conflict checking

Use this workflow when candidate hotstrings already exist and need to be checked
against the active hotstrings in a configured AutoCorrect2 project.

[`run_autocorrect2_check()`][hotstring.pipeline.run_autocorrect2_check] accepts
a sequence of
[`AutoCorrect2CandidateHotstring`][hotstring.autocorrect2.models.AutoCorrect2CandidateHotstring]
objects:

???+ info "Conflict Checking Workflow"

    ```mermaid
    flowchart TD
        A["Supplied candidates"] --> D["Resolve options and<br>assess conflicts"]
        B["Configured AutoCorrect2<br>source files"] --> C["Load existing<br>hotstrings"]
        C --> D
        D --> E["AutoCorrect2CheckResult"]
    ```

Typo generation is not involved. The returned
[`AutoCorrect2CheckResult`][hotstring.autocorrect2.models.AutoCorrect2CheckResult]
partitions the supplied candidates into accepted and rejected groups.

Each supplied candidate retains its semantic replacement and derives the
AutoCorrect2-compatible AutoHotkey content used when it is rendered.

The pipeline can optionally append accepted candidates to the generated include
file. The AutoCorrect2 writer owns the generated-file location and output
policy, while generic filesystem operations remain in
[`hotstring.file_io`][hotstring.file_io].

## Command-line usage

Supply candidates directly by repeating `--candidate`:

```powershell
uv run python -m hotstring autocorrect2-check `
    --candidate "teh" "the" "B0X" `
    --candidate "adn" "and" "B0X" `
    --project-dir "H:\Projects\AutoCorrect2" `
    --report .\reports\autocorrect2-check.txt
```

Each occurrence receives the semantic trigger, semantic replacement, and
hotstring option string.

Alternatively, use `--candidates-file` with a UTF-8 JSON array:

```json
[
  {
    "trigger": "teh",
    "replacement": "the",
    "options": "B0X"
  },
  {
    "trigger": "adn",
    "replacement": "and",
    "options": "B0X"
  }
]
```

```powershell
uv run python -m hotstring autocorrect2-check `
    --candidates-file .\candidates.json
```

`--candidate` and `--candidates-file` are mutually exclusive. The command is
read-only unless `--write-accepted` is supplied.

**See also:** [Command-line interface](../command-line.md) for project-directory resolution
and all command options.
