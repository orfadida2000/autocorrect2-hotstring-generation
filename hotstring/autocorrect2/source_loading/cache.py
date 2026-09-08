"""Persist AutoCorrect2 source fingerprints and extracted hotstrings.

The cache is an optimization only. SHA-256 of the exact source bytes is the
authoritative content identity; filesystem size and modification time are
stored as useful metadata but are never trusted as proof that a same-sized
source is unchanged.

Cached hotstrings persist only source-derived state: canonical AHK trigger
spelling and canonical option text. Semantic trigger text and the
case-insensitive semantic comparison key are reconstructed by the domain model on every
load so they always reflect the current trigger-normalization implementation.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import string
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, cast

from hotstring.constants import PROJECT_ROOT

from ...core.models import ExistingHotstring

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
"""Module logger used for cache diagnostics."""

CACHE_SCHEMA_VERSION: Final[int] = 2
"""Persistent-cache compatibility version, including parser semantics."""

DEFAULT_SOURCE_CACHE_PATH: Final[Path] = PROJECT_ROOT / ".cache" / "autocorrect2-source-cache.json"
"""Deterministic project-local path used for the persistent source cache."""


@dataclass(frozen=True, slots=True)
class CachedHotstring:
    """Represent the minimal persisted form of one extracted hotstring.

    Attributes:
        trigger:
            Canonical AHK source-form trigger text.
        options:
            Canonical hotstring option declaration.
    """

    trigger: str
    options: str


@dataclass(frozen=True, slots=True)
class SourceCacheEntry:
    """Represent cached state for one AutoCorrect2 source file.

    Attributes:
        modification_time_ns:
            Source modification time recorded when the entry was refreshed.
        size:
            Source size recorded when the entry was refreshed.
        sha256:
            SHA-256 digest of the exact source bytes.
        hotstrings:
            Extracted hotstrings stored in declaration order.
    """

    modification_time_ns: int
    size: int
    sha256: str
    hotstrings: tuple[CachedHotstring, ...]


@dataclass(slots=True)
class SourceCache:
    """Represent the complete persistent AutoCorrect2 source cache.

    Attributes:
        project_dir:
            Canonical AutoCorrect2 project directory associated with the
            cache. This prevents accidental reuse for a different checkout at
            another path; machine identity is deliberately not part of cache
            validity.
        files:
            Cache entries keyed by source path relative to the AutoCorrect2
            project root.
    """

    project_dir: str
    files: dict[str, SourceCacheEntry] = field(default_factory=dict)


def canonical_project_dir(project_dir: Path) -> str:
    """Return the canonical project-directory value stored in the cache.

    Args:
        project_dir:
            AutoCorrect2 project directory.

    Returns:
        Absolute normalized project-directory string.

    Raises:
        TypeError:
            If the supplied project directory is not a path.
        OSError:
            If path resolution fails.
    """
    if not isinstance(project_dir, Path):
        raise TypeError(
            f"AutoCorrect2 project directory must be a Path, not {type(project_dir).__name__}"
        )
    return str(project_dir.resolve())


def source_cache_key(source: Path) -> str:
    """Return the stable JSON key for a configured source path.

    Args:
        source:
            Source path relative to the AutoCorrect2 project root.

    Returns:
        POSIX-style relative path suitable for use as a JSON object key.

    Raises:
        TypeError:
            If the supplied source is not a path.
    """
    if not isinstance(source, Path):
        raise TypeError(f"Source cache key must be a Path, not {type(source).__name__}")
    return source.as_posix()


def compute_content_hash(content: bytes) -> str:
    """Compute the SHA-256 digest used as authoritative content identity.

    Args:
        content:
            Exact source-file bytes.

    Returns:
        Lowercase hexadecimal SHA-256 digest.

    Raises:
        TypeError:
            If the supplied content is not bytes.
    """
    if not isinstance(content, bytes):
        raise TypeError(f"Source content for hashing must be bytes, not {type(content).__name__}")

    digest = hashlib.sha256(content).hexdigest()
    LOGGER.debug("Computed SHA-256 digest for %d source byte(s).", len(content))
    return digest


def create_source_cache_entry(
    hotstrings: Sequence[ExistingHotstring],
    *,
    modification_time_ns: int,
    size: int,
    sha256: str,
) -> SourceCacheEntry:
    """Create a cache entry from parsed hotstrings and source state.

    Cached triggers use each model's canonical `ahk_trigger` field, not its
    semantic trigger. Restoring the entry therefore feeds exactly the input
    representation expected by `ExistingHotstring`.

    Args:
        hotstrings:
            Parsed hotstrings in declaration order.
        modification_time_ns:
            Current source modification time.
        size:
            Current source size.
        sha256:
            SHA-256 digest of the exact source bytes.

    Returns:
        Cache entry ready for persistence.

    Raises:
        TypeError:
            If source metadata or a hotstring has an invalid type.
        ValueError:
            If source metadata or the digest is invalid.
    """
    _validate_metadata(modification_time_ns, size, sha256)

    cached_hotstrings: list[CachedHotstring] = []
    for hotstring in hotstrings:
        if not isinstance(hotstring, ExistingHotstring):
            raise TypeError(
                "Cached hotstrings must contain ExistingHotstring instances, "
                f"not {type(hotstring).__name__}"
            )

        cached_hotstrings.append(
            CachedHotstring(
                trigger=hotstring.ahk_trigger,
                options=hotstring.options.declaration(),
            )
        )

    return SourceCacheEntry(
        modification_time_ns=modification_time_ns,
        size=size,
        sha256=sha256,
        hotstrings=tuple(cached_hotstrings),
    )


def restore_hotstrings(
    entry: SourceCacheEntry,
    *,
    source: Path,
) -> list[ExistingHotstring]:
    """Reconstruct domain hotstrings from one persisted cache entry.

    The cached trigger is intentionally fed back to `ExistingHotstring` as
    AHK source-form constructor input. Its semantic trigger, canonical source
    representation, parsed options, and case-insensitive semantic key are therefore
    rebuilt using the current code.

    Args:
        entry:
            Cached source entry to reconstruct.
        source:
            Source identifier assigned to each reconstructed hotstring.

    Returns:
        Existing hotstrings in their cached declaration order.

    Raises:
        TypeError:
            If the cache entry or source identifier has an invalid type.
        ValueError:
            If cached hotstring data is invalid under the current model.
    """
    if not isinstance(entry, SourceCacheEntry):
        raise TypeError(f"Source cache entry must be SourceCacheEntry, not {type(entry).__name__}")
    if not isinstance(source, Path):
        raise TypeError(f"Hotstring source identifier must be a Path, not {type(source).__name__}")

    hotstrings = [
        ExistingHotstring(
            trigger=hotstring.trigger,
            options_input=hotstring.options,
            source=source,
        )
        for hotstring in entry.hotstrings
    ]

    LOGGER.debug(
        "Reconstructed %d hotstring(s) from cached source %s.",
        len(hotstrings),
        source,
    )
    return hotstrings


def load_source_cache(cache_path: Path, *, project_dir: Path) -> SourceCache:
    """Load the persistent source cache or return an empty compatible cache.

    Missing, unreadable, malformed, incompatible, or project-mismatched cache
    files are treated as disposable optimization state. In those cases an
    empty cache associated with the requested AutoCorrect2 project is returned.

    Args:
        cache_path:
            JSON cache file to load.
        project_dir:
            AutoCorrect2 project directory expected by the caller.

    Returns:
        Loaded compatible cache, or a new empty cache when persisted state
        cannot be reused.

    Raises:
        TypeError:
            If a path argument has an invalid type.
        OSError:
            If canonicalizing the project directory fails.
    """
    if not isinstance(cache_path, Path):
        raise TypeError(f"Cache path must be a Path, not {type(cache_path).__name__}")

    expected_project_dir = canonical_project_dir(project_dir)

    try:
        raw_data: object = json.loads(cache_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        LOGGER.debug("Source cache does not exist at %s; starting empty.", cache_path)
        return SourceCache(project_dir=expected_project_dir)
    except (OSError, UnicodeError, json.JSONDecodeError):
        LOGGER.debug(
            "Source cache at %s could not be loaded; starting empty.",
            cache_path,
            exc_info=True,
        )
        return SourceCache(project_dir=expected_project_dir)

    if not isinstance(raw_data, dict):
        LOGGER.debug("Source cache at %s is not a JSON object; starting empty.", cache_path)
        return SourceCache(project_dir=expected_project_dir)

    data = cast(dict[str, object], raw_data)
    if data.get("schema_version") != CACHE_SCHEMA_VERSION:
        LOGGER.debug(
            "Source cache schema at %s is incompatible; expected %d and found %r.",
            cache_path,
            CACHE_SCHEMA_VERSION,
            data.get("schema_version"),
        )
        return SourceCache(project_dir=expected_project_dir)

    cached_project_dir = data.get("project_dir")
    if cached_project_dir != expected_project_dir:
        LOGGER.debug(
            "Source cache project mismatch at %s; cached=%r current=%r. Starting empty.",
            cache_path,
            cached_project_dir,
            expected_project_dir,
        )
        return SourceCache(project_dir=expected_project_dir)

    raw_files = data.get("files")
    if not isinstance(raw_files, dict):
        LOGGER.debug("Source cache files section at %s is invalid; starting empty.", cache_path)
        return SourceCache(project_dir=expected_project_dir)

    files: dict[str, SourceCacheEntry] = {}
    for source_key, raw_entry in raw_files.items():
        if not isinstance(source_key, str):
            LOGGER.debug("Ignoring source-cache entry with a non-string key: %r.", source_key)
            continue

        entry = _parse_source_cache_entry(raw_entry)
        if entry is None:
            LOGGER.debug("Ignoring malformed source-cache entry for %s.", source_key)
            continue
        files[source_key] = entry

    LOGGER.debug(
        "Loaded %d source-cache %s from %s.",
        len(files),
        "entry" if len(files) == 1 else "entries",
        cache_path,
    )
    return SourceCache(project_dir=expected_project_dir, files=files)


def save_source_cache(cache: SourceCache, cache_path: Path) -> None:
    """Persist the source cache atomically as UTF-8 JSON.

    Each cached hotstring contains exactly `trigger` and `options`. The trigger
    value is the canonical AHK source representation. Source paths are stored
    once as keys in the surrounding `files` object.

    Args:
        cache:
            Source cache to persist.
        cache_path:
            Destination JSON file.

    Raises:
        TypeError:
            If an argument has an invalid type.
        OSError:
            If the cache directory or cache file cannot be written or replaced.
    """
    if not isinstance(cache, SourceCache):
        raise TypeError(f"Cache must be SourceCache, not {type(cache).__name__}")
    if not isinstance(cache_path, Path):
        raise TypeError(f"Cache path must be a Path, not {type(cache_path).__name__}")

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(
            _serialize_source_cache(cache),
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{cache_path.name}.",
            suffix=".tmp",
            dir=cache_path.parent,
            delete=False,
        ) as temporary_file:
            temporary_file.write(payload)
            temporary_path = Path(temporary_file.name)

        os.replace(temporary_path, cache_path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise

    LOGGER.debug(
        "Persisted %d source-cache entr%s to %s.",
        len(cache.files),
        "y" if len(cache.files) == 1 else "ies",
        cache_path,
    )


def _parse_source_cache_entry(raw_entry: object) -> SourceCacheEntry | None:
    """Parse one untrusted JSON cache entry.

    Args:
        raw_entry:
            Decoded JSON value representing a source entry.

    Returns:
        Validated cache entry, or `None` when the value is malformed.
    """
    if not isinstance(raw_entry, dict):
        return None

    entry_data = cast(dict[str, object], raw_entry)
    modification_time_ns = entry_data.get("mtime_ns")
    size = entry_data.get("size")
    sha256 = entry_data.get("sha256")
    raw_hotstrings = entry_data.get("hotstrings")

    if not _metadata_is_valid(modification_time_ns, size, sha256):
        return None
    if not isinstance(raw_hotstrings, list):
        return None

    hotstrings: list[CachedHotstring] = []
    for raw_hotstring in raw_hotstrings:
        cached_hotstring = _parse_cached_hotstring(raw_hotstring)
        if cached_hotstring is None:
            return None
        hotstrings.append(cached_hotstring)

    return SourceCacheEntry(
        modification_time_ns=cast(int, modification_time_ns),
        size=cast(int, size),
        sha256=cast(str, sha256),
        hotstrings=tuple(hotstrings),
    )


def _parse_cached_hotstring(raw_hotstring: object) -> CachedHotstring | None:
    """Parse one minimal hotstring record from decoded JSON.

    Args:
        raw_hotstring:
            Decoded JSON value representing one cached hotstring.

    Returns:
        Parsed cached hotstring, or `None` when malformed.
    """
    if not isinstance(raw_hotstring, dict):
        return None

    hotstring_data = cast(dict[str, object], raw_hotstring)
    if set(hotstring_data) != {"trigger", "options"}:
        return None

    trigger = hotstring_data.get("trigger")
    options = hotstring_data.get("options")
    if not isinstance(trigger, str) or not isinstance(options, str):
        return None

    return CachedHotstring(trigger=trigger, options=options)


def _serialize_source_cache(cache: SourceCache) -> dict[str, object]:
    """Convert the in-memory source cache to JSON-compatible values.

    Args:
        cache:
            Source cache to serialize.

    Returns:
        JSON-compatible cache document.
    """
    files: dict[str, object] = {}
    for source_key, entry in sorted(cache.files.items()):
        files[source_key] = {
            "mtime_ns": entry.modification_time_ns,
            "size": entry.size,
            "sha256": entry.sha256,
            "hotstrings": [
                {
                    "trigger": hotstring.trigger,
                    "options": hotstring.options,
                }
                for hotstring in entry.hotstrings
            ],
        }

    return {
        "schema_version": CACHE_SCHEMA_VERSION,
        "project_dir": cache.project_dir,
        "files": files,
    }


def _validate_metadata(modification_time_ns: int, size: int, sha256: str) -> None:
    """Validate metadata used to construct a source-cache entry.

    Args:
        modification_time_ns:
            Source modification time.
        size:
            Source size.
        sha256:
            Source SHA-256 digest.

    Raises:
        TypeError:
            If a metadata value has an invalid type.
        ValueError:
            If a metadata value is outside its valid domain.
    """
    if isinstance(modification_time_ns, bool) or not isinstance(modification_time_ns, int):
        raise TypeError("Source modification time must be an integer.")
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("Source size must be an integer.")
    if not isinstance(sha256, str):
        raise TypeError("Source SHA-256 digest must be a string.")

    if modification_time_ns < 0:
        raise ValueError("Source modification time cannot be negative.")
    if size < 0:
        raise ValueError("Source size cannot be negative.")
    if not _sha256_is_valid(sha256):
        raise ValueError("Source SHA-256 digest must be 64 hexadecimal characters.")


def _metadata_is_valid(
    modification_time_ns: object,
    size: object,
    sha256: object,
) -> bool:
    """Return whether decoded source metadata has the expected shape.

    Args:
        modification_time_ns:
            Decoded modification-time value.
        size:
            Decoded file-size value.
        sha256:
            Decoded digest value.

    Returns:
        Whether all metadata values are valid.
    """
    return (
        isinstance(modification_time_ns, int)
        and not isinstance(modification_time_ns, bool)
        and modification_time_ns >= 0
        and isinstance(size, int)
        and not isinstance(size, bool)
        and size >= 0
        and isinstance(sha256, str)
        and _sha256_is_valid(sha256)
    )


def _sha256_is_valid(value: str) -> bool:
    """Return whether a string is a lowercase-or-uppercase SHA-256 hex digest.

    Args:
        value:
            Candidate digest string.

    Returns:
        Whether the value contains exactly 64 hexadecimal characters.
    """
    return len(value) == 64 and all(character in string.hexdigits for character in value)
