# AutoCorrect2 Hotstring Generation

This project generates realistic keyboard typos, removes ambiguous generated
mappings, checks the remaining candidates against active AutoCorrect2
hotstrings, and can append approved definitions to a dedicated generated AHK
include file.

The two main subsystems are independent. You can run typo generation without
AutoCorrect2, or check manually created candidates without generating typos.
