"""Load AutoCorrect2 hotstrings from source files with persistent caching.

The package keeps source parsing, cache persistence, and multi-file loading as
separate concerns. Callers normally use [`load_existing_hotstrings()`]
[hotstring.autocorrect2.source_loading.loader.load_existing_hotstrings].
"""

from .cache import DEFAULT_SOURCE_CACHE_PATH
from .loader import load_existing_hotstrings
from .parser import HOTSTRING_PATTERN, extract_hotstrings

__all__ = [
    "DEFAULT_SOURCE_CACHE_PATH",
    "HOTSTRING_PATTERN",
    "extract_hotstrings",
    "load_existing_hotstrings",
]
