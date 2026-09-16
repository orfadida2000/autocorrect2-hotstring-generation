"""Resolve parsed CLI input into immutable runtime command objects.

This module owns the application-specific boundary between `argparse` values
and the project's domain APIs. It loads word and candidate files, constructs
[`TypoGenerationTask`][hotstring.typo_generation.models.TypoGenerationTask]
objects, resolves the AutoCorrect2 project directory, and validates paths
before a pipeline starts.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from dotenv import dotenv_values

from ..autocorrect2.constants import REQUIRED_HOTSTRING_SOURCE_RELATIVE_PATHS
from ..autocorrect2.models import AutoCorrect2CandidateHotstring
from ..constants import PROJECT_ROOT
from ..typo_generation.models import (
    TypoGenerationConfig,
    TypoGenerationTask,
    create_default_typo_generation_tasks,
)

AUTOCORRECT2_PROJECT_DIR_ENV: Final[str] = "AUTOCORRECT2_PROJECT_DIR"
"""Environment variable containing the local AutoCorrect2 project path."""

DEFAULT_ENV_FILE: Final[Path] = PROJECT_ROOT / ".env"
"""Project-local dotenv file consulted as the final configuration source."""

_CANDIDATE_FIELDS: Final[frozenset[str]] = frozenset({"trigger", "replacement", "options"})


class CliConfigurationError(ValueError):
    """Indicate invalid runtime configuration supplied through the CLI."""


@dataclass(frozen=True, slots=True)
class GenerationRuntimeConfig:
    """Store resolved inputs shared by typo-generating workflows.

    Attributes:
        words:
            Ordered, de-duplicated source words.
        tasks:
            Ordered typo-generation tasks derived from CLI settings.
        config:
            Shared MULTYPO generator configuration.
        n_workers:
            Optional process-pool size.
    """

    words: tuple[str, ...]
    tasks: tuple[TypoGenerationTask, ...]
    config: TypoGenerationConfig
    n_workers: int | None


@dataclass(frozen=True, slots=True)
class AutoCorrect2RuntimeConfig:
    """Store resolved inputs shared by AutoCorrect2-aware workflows.

    Attributes:
        project_dir:
            Validated AutoCorrect2 project directory.
        write_accepted:
            Whether accepted candidates may be appended to the generated
            include file.
    """

    project_dir: Path
    write_accepted: bool


@dataclass(frozen=True, slots=True)
class TypoGenerationCommand:
    """Represent one standalone typo-generation invocation.

    Attributes:
        generation:
            Resolved typo-generation inputs.
        report_path:
            Optional report destination.
    """

    generation: GenerationRuntimeConfig
    report_path: Path | None


@dataclass(frozen=True, slots=True)
class AutoCorrect2CheckCommand:
    """Represent one standalone AutoCorrect2 conflict-check invocation.

    Attributes:
        candidates:
            Candidate hotstrings supplied directly by the user.
        autocorrect2:
            Resolved AutoCorrect2 integration settings.
        report_path:
            Optional report destination.
    """

    candidates: tuple[AutoCorrect2CandidateHotstring, ...]
    autocorrect2: AutoCorrect2RuntimeConfig
    report_path: Path | None


@dataclass(frozen=True, slots=True)
class FullPipelineCommand:
    """Represent one composed generation-and-check invocation.

    Attributes:
        generation:
            Resolved typo-generation inputs.
        autocorrect2:
            Resolved AutoCorrect2 integration settings.
        report_path:
            Optional combined report destination.
    """

    generation: GenerationRuntimeConfig
    autocorrect2: AutoCorrect2RuntimeConfig
    report_path: Path | None


type CommandConfig = TypoGenerationCommand | AutoCorrect2CheckCommand | FullPipelineCommand
"""Union of all command objects accepted by the execution layer."""


def create_command_config(namespace: argparse.Namespace) -> CommandConfig:
    """Convert parsed arguments into one validated command object.

    Args:
        namespace:
            Namespace returned by
            [`create_argument_parser()`][hotstring.cli.parser.create_argument_parser].

    Returns:
        Immutable configuration for the selected workflow.

    Raises:
        CliConfigurationError:
            If a file, path, environment value, candidate, or domain setting
            is invalid.
    """
    try:
        report_path = _optional_cli_path(namespace.report)

        if namespace.command == "typo-generation":
            return TypoGenerationCommand(
                generation=_create_generation_config(namespace),
                report_path=report_path,
            )
        if namespace.command == "autocorrect2-check":
            return AutoCorrect2CheckCommand(
                candidates=_load_candidates(namespace),
                autocorrect2=_create_autocorrect2_config(namespace),
                report_path=report_path,
            )
        if namespace.command == "full-pipeline":
            return FullPipelineCommand(
                generation=_create_generation_config(namespace),
                autocorrect2=_create_autocorrect2_config(namespace),
                report_path=report_path,
            )
    except CliConfigurationError:
        raise
    except (OSError, TypeError, ValueError) as exc:
        raise CliConfigurationError(str(exc)) from exc

    raise CliConfigurationError(f"Unsupported command: {namespace.command!r}")


def _create_generation_config(namespace: argparse.Namespace) -> GenerationRuntimeConfig:
    """Build the shared typo-generation runtime configuration.

    Args:
        namespace:
            Parsed command arguments.

    Returns:
        Resolved generation configuration.
    """
    weights = tuple(float(value) for value in namespace.keyboard_neighbor_weights)
    config = TypoGenerationConfig(
        language=namespace.language,
        use_excluding_set=namespace.excluding_set,
        horizontal_vs_vertical=(weights[0], weights[1]),
    )
    tasks = create_default_typo_generation_tasks(
        single_error_attempts_per_word=namespace.single_error_attempts_per_word,
        multi_error_attempts_per_word=namespace.multi_error_attempts_per_word,
        multi_error_minimum_word_length=namespace.multi_error_minimum_word_length,
    )
    return GenerationRuntimeConfig(
        words=_load_words(namespace),
        tasks=tasks,
        config=config,
        n_workers=namespace.workers,
    )


def _create_autocorrect2_config(
    namespace: argparse.Namespace,
) -> AutoCorrect2RuntimeConfig:
    """Build the shared AutoCorrect2 runtime configuration.

    Args:
        namespace:
            Parsed command arguments.

    Returns:
        Resolved AutoCorrect2 configuration.
    """
    project_dir = _resolve_autocorrect2_project_dir(
        direct_path=namespace.autocorrect2_project_dir,
        explicit_env_file=namespace.env_file,
    )
    return AutoCorrect2RuntimeConfig(
        project_dir=project_dir,
        write_accepted=namespace.write_accepted,
    )


def _load_words(namespace: argparse.Namespace) -> tuple[str, ...]:
    """Load, normalize, and de-duplicate source words.

    Args:
        namespace:
            Parsed command arguments.

    Returns:
        Ordered source-word tuple.

    Raises:
        CliConfigurationError:
            If the word source is unreadable or contains no usable words.
    """
    if namespace.word is not None:
        raw_words = namespace.word
        source_description = "--word"
    else:
        path = _require_input_file(namespace.words_file, label="word-list file")
        try:
            raw_words = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as exc:
            raise CliConfigurationError(f"Could not read word-list file {path}: {exc}") from exc
        source_description = str(path)

    words = _unique_nonempty_text(raw_words)
    if not words:
        raise CliConfigurationError(
            f"The word source {source_description} contains no non-empty words."
        )
    return words


def _load_candidates(
    namespace: argparse.Namespace,
) -> tuple[AutoCorrect2CandidateHotstring, ...]:
    """Load and validate directly supplied candidate hotstrings.

    Args:
        namespace:
            Parsed command arguments.

    Returns:
        Candidate tuple in source order.

    Raises:
        CliConfigurationError:
            If candidate data is missing, malformed, or invalid.
    """
    if namespace.candidate is not None:
        records: Sequence[object] = namespace.candidate
    else:
        path = _require_input_file(namespace.candidates_file, label="candidate JSON file")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CliConfigurationError(
                f"Could not read candidate JSON file {path}: {exc}"
            ) from exc
        if not isinstance(document, list):
            raise CliConfigurationError(
                f"Candidate JSON file {path} must contain a top-level array."
            )
        records = document

    if not records:
        raise CliConfigurationError("At least one candidate must be supplied.")

    candidates: list[AutoCorrect2CandidateHotstring] = []
    for index, record in enumerate(records, start=1):
        try:
            trigger, replacement, options = _candidate_fields(record)
            candidates.append(
                AutoCorrect2CandidateHotstring(
                    trigger=trigger,
                    replacement=replacement,
                    options_input=options,
                )
            )
        except (TypeError, ValueError) as exc:
            raise CliConfigurationError(f"Candidate {index} is invalid: {exc}") from exc
    return tuple(candidates)


def _candidate_fields(record: object) -> tuple[str, str, str]:
    """Extract the three candidate fields from CLI or JSON input.

    Args:
        record:
            Three-value CLI sequence or JSON object.

    Returns:
        Semantic trigger, semantic replacement, and option declaration.

    Raises:
        TypeError:
            If the record shape or a field type is invalid.
        ValueError:
            If a JSON object has missing or unexpected fields.
    """
    if isinstance(record, Mapping):
        keys = set(record)
        missing = _CANDIDATE_FIELDS - keys
        unexpected = keys - _CANDIDATE_FIELDS
        if missing:
            raise ValueError(f"missing fields: {', '.join(sorted(missing))}")
        if unexpected:
            raise ValueError(f"unexpected fields: {', '.join(sorted(unexpected))}")
        trigger, replacement, options = (
            record["trigger"],
            record["replacement"],
            record["options"],
        )
    elif isinstance(record, Sequence) and not isinstance(record, (str, bytes)):
        if len(record) != 3:
            raise ValueError("expected exactly three values")
        trigger, replacement, options = record
    else:
        raise TypeError("expected an object with trigger, replacement, and options fields")

    if (
        not isinstance(trigger, str)
        or not isinstance(replacement, str)
        or not isinstance(options, str)
    ):
        raise TypeError("trigger, replacement, and options must all be strings")
    return trigger, replacement, options


def _resolve_autocorrect2_project_dir(
    *,
    direct_path: Path | None,
    explicit_env_file: Path | None,
) -> Path:
    """Resolve the AutoCorrect2 project path by documented precedence.

    Resolution stops at the first configured source:

    1. `--project-dir`;
    2. the process environment;
    3. an explicitly selected `--env-file`;
    4. the project-root `.env` file.

    Lower-priority sources are not opened or validated after a higher-priority
    value is found.

    Args:
        direct_path:
            Optional path supplied directly on the command line.
        explicit_env_file:
            Optional dotenv file selected on the command line.

    Returns:
        Validated absolute AutoCorrect2 project path.

    Raises:
        CliConfigurationError:
            If no source supplies a usable path or the selected project is
            invalid.
    """
    if direct_path is not None:
        return _validate_autocorrect2_project_dir(_absolute_path(direct_path))

    process_value = os.environ.get(AUTOCORRECT2_PROJECT_DIR_ENV)
    if process_value is not None:
        if not process_value.strip():
            raise CliConfigurationError(f"{AUTOCORRECT2_PROJECT_DIR_ENV} is set but empty.")
        return _validate_autocorrect2_project_dir(_absolute_path(Path(process_value.strip())))

    if explicit_env_file is not None:
        env_file = _require_input_file(explicit_env_file, label="dotenv file")
        return _project_dir_from_dotenv(env_file)

    if DEFAULT_ENV_FILE.is_file():
        return _project_dir_from_dotenv(DEFAULT_ENV_FILE)

    raise CliConfigurationError(
        "AutoCorrect2 project directory is not configured. Supply --project-dir, "
        f"set {AUTOCORRECT2_PROJECT_DIR_ENV}, pass --env-file, or create "
        f"{DEFAULT_ENV_FILE}."
    )


def _project_dir_from_dotenv(env_file: Path) -> Path:
    """Read and validate the AutoCorrect2 path from one dotenv file.

    Relative values are interpreted from the dotenv file's directory, making
    project-local configuration independent of the caller's working directory.

    Args:
        env_file:
            Existing dotenv file to read.

    Returns:
        Validated absolute AutoCorrect2 project path.

    Raises:
        CliConfigurationError:
            If the variable is absent, empty, or resolves to an invalid
            project directory.
    """
    try:
        values = dotenv_values(env_file)
    except OSError as exc:
        raise CliConfigurationError(f"Could not read dotenv file {env_file}: {exc}") from exc

    raw_value = values.get(AUTOCORRECT2_PROJECT_DIR_ENV)
    if raw_value is None or not raw_value.strip():
        raise CliConfigurationError(
            f"Dotenv file {env_file} does not define a non-empty {AUTOCORRECT2_PROJECT_DIR_ENV}."
        )

    path = Path(raw_value.strip()).expanduser()
    if not path.is_absolute():
        path = env_file.parent / path
    return _validate_autocorrect2_project_dir(path.resolve(strict=False))


def _validate_autocorrect2_project_dir(path: Path) -> Path:
    """Validate the selected AutoCorrect2 project directory.

    Args:
        path:
            Absolute candidate directory.

    Returns:
        The validated path.

    Raises:
        CliConfigurationError:
            If the directory or a required hotstring source is missing.
    """
    if not path.is_dir():
        raise CliConfigurationError(f"AutoCorrect2 project directory does not exist: {path}")

    missing = [
        relative_path
        for relative_path in REQUIRED_HOTSTRING_SOURCE_RELATIVE_PATHS
        if not (path / relative_path).is_file()
    ]
    if missing:
        rendered = ", ".join(str(relative_path) for relative_path in missing)
        raise CliConfigurationError(
            f"AutoCorrect2 project directory {path} is missing required files: {rendered}"
        )
    return path


def _require_input_file(path: Path, *, label: str) -> Path:
    """Resolve a CLI path and require an existing regular file.

    Args:
        path:
            Path supplied on the command line.
        label:
            Human-readable input name used in an error message.

    Returns:
        Absolute file path.

    Raises:
        CliConfigurationError:
            If the path is not an existing regular file.
    """
    absolute = _absolute_path(path)
    if not absolute.is_file():
        raise CliConfigurationError(f"The {label} does not exist: {absolute}")
    return absolute


def _optional_cli_path(path: Path | None) -> Path | None:
    """Resolve an optional CLI path against the current directory.

    Args:
        path:
            Optional path supplied on the command line.

    Returns:
        Absolute path, or `None` when no path was supplied.
    """
    return None if path is None else _absolute_path(path)


def _absolute_path(path: Path) -> Path:
    """Return an expanded absolute path without requiring it to exist.

    Args:
        path:
            Path to normalize.

    Returns:
        Expanded absolute path.
    """
    return path.expanduser().resolve(strict=False)


def _unique_nonempty_text(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize text values and remove duplicates while preserving order.

    Args:
        values:
            Text values to normalize.

    Returns:
        Ordered tuple of unique, non-empty stripped values.
    """
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
