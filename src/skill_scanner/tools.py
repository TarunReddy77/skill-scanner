"""The only two things the scanning model may do: list files and read files inside one skill folder.
Plain functions, no dependency on the agent framework. Nothing here can run or execute anything."""

import json
import re
from pathlib import Path

from skill_scanner.scanner import MAX_FILE_BYTES, Unscannable, skill_paths


class ToolRefused(Exception):
    """The model asked for something it is not allowed to do. The message says why."""


def read_file(folder: str, path: str) -> str:
    root = Path(folder).resolve()
    requested = root / path
    if any(part.is_symlink() for part in [requested, *requested.parents] if part != root and root in part.parents):
        raise ToolRefused(f"symlinks are not allowed: {path}")
    target = requested.resolve()
    if not target.is_relative_to(root):
        raise ToolRefused(f"path is outside the skill folder: {path}")
    if not target.is_file():
        raise ToolRefused(f"not a file: {path}")
    if target.stat().st_size > MAX_FILE_BYTES:
        raise Unscannable(f"file too large to be scanned: {path}")
    # Python has already turned \r\n and \r into \n. Do not use splitlines(): it also splits on \x0b, \x0c and
    # U+2028, which would make our line numbers differ from the ones a person sees in an editor.
    lines = target.read_text(encoding="utf-8").split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return "\n".join(json.dumps({"line": n, "text": text}) for n, text in enumerate(lines, start=1))


def list_files(folder: str) -> list[str]:
    root = Path(folder).resolve()
    return sorted(p.relative_to(root).as_posix() for p in skill_paths(root) if p.is_file())
