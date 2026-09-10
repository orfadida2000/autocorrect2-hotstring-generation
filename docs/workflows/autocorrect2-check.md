# AutoCorrect2 check only

```text
manually supplied AutoCorrect2CandidateHotstring objects
        ↓
load configured AutoCorrect2 hotstrings
        ↓
resolve declaration options against applicable defaults
        ↓
generic conflict checking
        ↓
AutoCorrect2CheckResult
```

Typo generation is not required. Each candidate retains its semantic
replacement and derives its AutoCorrect2 executable content through the
concrete candidate subclass.

The pipeline can optionally append accepted candidates to the generated include
file. The AutoCorrect2 writer owns the generated-file location and output
policy, while generic filesystem operations remain in
[`hotstring.file_io`][hotstring.file_io].
