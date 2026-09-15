"""Load configured AutoCorrect2 hotstring sources through a persistent cache."""

from __future__ import annotations

import logging
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from ...core.models import ExistingHotstring
from ..constants import (
    OPTIONAL_HOTSTRING_SOURCE_RELATIVE_PATHS,
    REQUIRED_HOTSTRING_SOURCE_RELATIVE_PATHS,
)
from .cache import (
    DEFAULT_SOURCE_CACHE_PATH,
    SourceCache,
    SourceCacheEntry,
    compute_content_hash,
    create_source_cache_entry,
    load_source_cache,
    restore_hotstrings,
    save_source_cache,
    source_cache_key,
)
from .parser import extract_hotstrings

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)
"""Module logger used for source-loading diagnostics."""


def load_existing_hotstrings(
    project_dir: Path,
    *,
    required_source_paths: Sequence[Path] = REQUIRED_HOTSTRING_SOURCE_RELATIVE_PATHS,
    optional_source_paths: Sequence[Path] = OPTIONAL_HOTSTRING_SOURCE_RELATIVE_PATHS,
    cache_path: Path | None = DEFAULT_SOURCE_CACHE_PATH,
) -> list[ExistingHotstring]:
    """Load all configured active static AutoCorrect2 hotstrings.

    Required sources must exist. Optional sources, including the project-owned
    generated include file, are scanned only when present. When caching is
    enabled, SHA-256 is the authoritative content identity. File size and
    modification time are retained as useful metadata and positive change
    signals, but matching metadata never suppresses hash verification.

    Cache failures are treated as optimization failures rather than source-load
    failures. The function falls back to parsing authoritative AutoCorrect2
    source files when persisted cache data cannot be used.

    Args:
        project_dir:
            AutoCorrect2 project directory.
        required_source_paths:
            Relative source paths that must exist.
        optional_source_paths:
            Relative source paths scanned when present.
        cache_path:
            Persistent JSON cache path, or `None` to disable caching.

    Returns:
        Existing hotstrings in source-file and declaration order.

    Raises:
        TypeError:
            If a path argument has an invalid type.
        FileNotFoundError:
            If a required source does not exist.
        UnicodeDecodeError:
            If a changed source is not valid UTF-8 text.
        ValueError:
            If a parsed hotstring declaration is invalid.
        OSError:
            If an authoritative source cannot be inspected or read.
    """
    if not isinstance(project_dir, Path):
        raise TypeError(
            f"AutoCorrect2 project directory must be a Path, not {type(project_dir).__name__}"
        )
    if cache_path is not None and not isinstance(cache_path, Path):
        raise TypeError(
            f"Source cache path must be a Path or None, not {type(cache_path).__name__}"
        )

    LOGGER.debug("Loading AutoCorrect2 hotstrings from project %s.", project_dir)

    cache = (
        load_source_cache(cache_path, project_dir=project_dir) if cache_path is not None else None
    )
    cache_dirty = False
    hotstrings: list[ExistingHotstring] = []

    for relative_path in required_source_paths:
        file_path = project_dir / relative_path
        if not file_path.is_file():
            LOGGER.debug("Required hotstring source is missing: %s.", file_path)
            raise FileNotFoundError(f"Hotstring source file was not found: {file_path}")

        loaded, source_cache_changed = _load_source_hotstrings(
            file_path,
            source=relative_path,
            cache=cache,
        )
        hotstrings.extend(loaded)
        cache_dirty = cache_dirty or source_cache_changed

    for relative_path in optional_source_paths:
        file_path = project_dir / relative_path
        if not file_path.is_file():
            LOGGER.debug(
                "Optional hotstring source is absent and will be skipped: %s.",
                file_path,
            )
            if cache is not None:
                source_key = source_cache_key(relative_path)
                if cache.files.pop(source_key, None) is not None:
                    LOGGER.debug(
                        "Removed stale cache entry for absent optional source %s.",
                        relative_path,
                    )
                    cache_dirty = True
            continue

        loaded, source_cache_changed = _load_source_hotstrings(
            file_path,
            source=relative_path,
            cache=cache,
        )
        hotstrings.extend(loaded)
        cache_dirty = cache_dirty or source_cache_changed

    if cache is not None and cache_dirty and cache_path is not None:
        try:
            save_source_cache(cache, cache_path)
        except OSError:
            LOGGER.debug(
                "Updated source cache could not be persisted to %s; continuing without failure.",
                cache_path,
                exc_info=True,
            )
    elif cache is not None:
        LOGGER.debug("Source cache remained unchanged; no cache write is required.")

    LOGGER.debug("Loaded %d existing AutoCorrect2 hotstring(s).", len(hotstrings))
    return hotstrings


def _load_source_hotstrings(
    file_path: Path,
    *,
    source: Path,
    cache: SourceCache | None,
) -> tuple[list[ExistingHotstring], bool]:
    """Load one source using cache reuse when its content hash matches.

    Args:
        file_path:
            Authoritative source file to inspect.
        source:
            Relative source identifier stored on extracted hotstrings.
        cache:
            Loaded persistent cache, or `None` when caching is disabled.

    Returns:
        Pair containing loaded hotstrings and whether the in-memory cache was
        modified.

    Raises:
        UnicodeDecodeError:
            If source bytes requiring parsing are not valid UTF-8 text.
        ValueError:
            If a parsed hotstring declaration is invalid.
        OSError:
            If the source cannot be inspected or read.
    """
    if cache is None:
        LOGGER.debug("Cache disabled for source %s; parsing authoritative file.", source)
        content = file_path.read_bytes()
        return _parse_source_content(content, source=source), False

    source_key = source_cache_key(source)
    cached_entry = cache.files.get(source_key)
    source_stat = file_path.stat()

    if cached_entry is None:
        LOGGER.debug("Cache miss for source %s; parsing authoritative file.", source)
        return _parse_and_refresh_source(
            file_path,
            source=source,
            source_key=source_key,
            source_stat=source_stat,
            cache=cache,
        )

    if source_stat.st_size != cached_entry.size:
        LOGGER.debug(
            "Source size changed for %s (%d -> %d); reparsing without old-hash comparison.",
            source,
            cached_entry.size,
            source_stat.st_size,
        )
        return _parse_and_refresh_source(
            file_path,
            source=source,
            source_key=source_key,
            source_stat=source_stat,
            cache=cache,
        )

    if source_stat.st_mtime_ns != cached_entry.modification_time_ns:
        LOGGER.debug("Source modification time changed for %s; verifying content hash.", source)
    else:
        LOGGER.debug(
            "Source size and modification time match cache for %s; verifying content hash anyway.",
            source,
        )

    content = file_path.read_bytes()
    current_hash = compute_content_hash(content)

    if current_hash != cached_entry.sha256:
        LOGGER.debug("Content hash changed for source %s; reparsing.", source)
        return _parse_and_refresh_source(
            file_path,
            source=source,
            source_key=source_key,
            source_stat=source_stat,
            cache=cache,
            content=content,
            content_hash=current_hash,
        )

    try:
        hotstrings = restore_hotstrings(cached_entry, source=source)
    except (TypeError, ValueError):
        LOGGER.debug(
            "Cached parsed hotstrings for %s are incompatible; reparsing authoritative content.",
            source,
            exc_info=True,
        )
        return _parse_and_refresh_source(
            file_path,
            source=source,
            source_key=source_key,
            source_stat=source_stat,
            cache=cache,
            content=content,
            content_hash=current_hash,
        )

    cache_changed = False
    if source_stat.st_mtime_ns != cached_entry.modification_time_ns:
        cache.files[source_key] = SourceCacheEntry(
            modification_time_ns=source_stat.st_mtime_ns,
            size=source_stat.st_size,
            sha256=cached_entry.sha256,
            hotstrings=cached_entry.hotstrings,
        )
        cache_changed = True
        LOGGER.debug(
            "Content for %s is unchanged; refreshed cached filesystem metadata only.",
            source,
        )
    else:
        LOGGER.debug("Cache hit for source %s; reused extracted hotstrings.", source)

    return hotstrings, cache_changed


def _parse_and_refresh_source(
    file_path: Path,
    *,
    source: Path,
    source_key: str,
    source_stat: os.stat_result,
    cache: SourceCache,
    content: bytes | None = None,
    content_hash: str | None = None,
) -> tuple[list[ExistingHotstring], bool]:
    """Parse one authoritative source and replace its cache entry.

    Args:
        file_path:
            Source file used when bytes have not already been read.
        source:
            Relative source identifier stored on extracted hotstrings.
        source_key:
            Stable cache key for the source.
        source_stat:
            Filesystem metadata captured before parsing.
        cache:
            In-memory source cache to update.
        content:
            Already-read source bytes when available.
        content_hash:
            Already-computed source digest when available.

    Returns:
        Pair containing parsed hotstrings and `True` to indicate that the cache
        was refreshed.

    Raises:
        TypeError:
            If the supplied filesystem metadata is invalid.
        UnicodeDecodeError:
            If source bytes are not valid UTF-8 text.
        ValueError:
            If a parsed hotstring declaration is invalid.
        OSError:
            If source bytes must be read and the read fails.
    """
    if content is None:
        content = file_path.read_bytes()
    if content_hash is None:
        content_hash = compute_content_hash(content)

    hotstrings = _parse_source_content(content, source=source)

    modification_time_ns = getattr(source_stat, "st_mtime_ns", None)
    size = getattr(source_stat, "st_size", None)
    if not isinstance(modification_time_ns, int) or isinstance(modification_time_ns, bool):
        raise TypeError("Source stat result does not provide a valid st_mtime_ns value.")
    if not isinstance(size, int) or isinstance(size, bool):
        raise TypeError("Source stat result does not provide a valid st_size value.")

    cache.files[source_key] = create_source_cache_entry(
        hotstrings,
        modification_time_ns=modification_time_ns,
        size=size,
        sha256=content_hash,
    )
    LOGGER.debug(
        "Refreshed cache entry for source %s with %d parsed hotstring(s).",
        source,
        len(hotstrings),
    )
    return hotstrings, True


def _parse_source_content(content: bytes, *, source: Path) -> list[ExistingHotstring]:
    """Decode source bytes and delegate static declaration parsing.

    Args:
        content:
            Exact source-file bytes.
        source:
            Relative source identifier stored on extracted hotstrings.

    Returns:
        Parsed existing hotstrings in declaration order.

    Raises:
        UnicodeDecodeError:
            If the source is not valid UTF-8 text.
        ValueError:
            If an extracted hotstring declaration is invalid.
    """
    LOGGER.debug("Decoding authoritative source %s for parsing.", source)
    return extract_hotstrings(content.decode("utf-8-sig"), source=source)
