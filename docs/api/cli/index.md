# Command-line interface API

`hotstring.cli` contains the application layer for the project's command-line
interface. It converts command-line input into validated runtime objects and
dispatches those objects to the public pipeline APIs.

The subpackage does not implement typo generation, conflict detection, source
loading, or generated-file writing. Those responsibilities remain in their
respective domain and pipeline modules.

The subpackage contains:

- [Application](application.md), which defines the CLI entry point, logging
  setup, process-level error handling, and exit statuses;
- [Parser](parser.md), which defines the top-level parser, the three
  subcommands, and their arguments;
- [Runtime configuration](runtime.md), which loads external inputs, resolves
  the AutoCorrect2 project directory, constructs typo-generation tasks, and
  creates immutable command objects;
- [Command execution](commands.md), which dispatches validated command objects
  to the corresponding pipeline functions and prints terminal summaries.

The package root re-exports
[`main()`][hotstring.cli.application.main], allowing the repository-level
`main.py` entry point to import it with:

```python
from hotstring.cli import main
```
