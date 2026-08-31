"""Provide small generic text-file I/O helpers."""

from __future__ import annotations

from pathlib import Path


def read_text(path: Path, *, encoding: str = "utf-8") -> str:
    """Read a text file.

    Args:
        path:
            File to read.
        encoding:
            Text encoding.

    Returns:
        File contents.

    Raises:
        OSError:
            If the file cannot be read.
    """
    return path.read_text(encoding=encoding)


def write_text(
    path: Path,
    text: str,
    *,
    append: bool = False,
    encoding: str = "utf-8",
    create_parents: bool = True,
) -> None:
    """Write or append text to a file.

    Args:
        path:
            Destination file.
        text:
            Text to write.
        append:
            Append instead of replacing the current contents.
        encoding:
            Text encoding.
        create_parents:
            Create missing parent directories before writing.

    Raises:
        OSError:
            If the destination cannot be written.
    """
    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"
    with path.open(mode, encoding=encoding, newline="") as stream:
        stream.write(text)
