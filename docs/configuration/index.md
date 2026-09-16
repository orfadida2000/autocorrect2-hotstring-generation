# Configuration

Configuration is divided between AutoCorrect2 integration and typo-generation
behavior. These concerns are independent: standalone typo generation does not
require an AutoCorrect2 project directory.

## AutoCorrect2 integration

[AutoCorrect2 configuration](autocorrect2.md) explains how the local
AutoCorrect2 project directory is resolved, including command-line,
environment-variable, and dotenv sources. It also describes generated output
and the explicit `--write-accepted` requirement.

## Typo generation

[Typo-generation configuration](typo-generation.md) describes the generation
settings represented by
[`TypoGenerationConfig`][hotstring.typo_generation.models.TypoGenerationConfig],
the ordered
[`TypoGenerationTask`][hotstring.typo_generation.models.TypoGenerationTask]
sequence, and execution settings such as the worker count.

**See also:** [Command-line interface](../command-line.md) for command syntax
and all command options.
