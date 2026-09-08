from pathlib import Path
from typing import Final

TOP_PACKAGE_DIR: Final[Path] = Path(__file__).parent
"""Top-level package directory of this source project."""

PROJECT_ROOT: Final[Path] = TOP_PACKAGE_DIR.parent
"""Root directory of this source project."""
