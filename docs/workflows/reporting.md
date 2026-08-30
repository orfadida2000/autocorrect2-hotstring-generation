# Reporting

Report builders return `list[str]` and never write files themselves:

- `create_typo_generation_report()`
- `create_autocorrect2_report()`
- `create_full_pipeline_report()`

The full report reuses the two stage-specific report bodies. Run-level
framing is added once by `build_report_document()`. No date or timestamp is
currently inserted; future run-level metadata belongs in that wrapper.

Only the pipeline layer decides when a report is written and delegates the
filesystem operation to `hotstring.file_io`.
