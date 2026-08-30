# AutoCorrect2 check only

```text
manually supplied AutoCorrect2CandidateHotstring objects
        ↓
load active static AutoCorrect2 hotstrings
        ↓
generic conflict checking
        ↓
AutoCorrect2CheckResult
```

Typo generation is not required. The pipeline can optionally append accepted
candidates to the generated include file, but the writer enforces the
AutoCorrect2-generated `B0X` contract independently of conflict checking.
