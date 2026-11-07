"""Core scan logic. The model is passed in as a plain function, so nothing here depends on the agent framework."""

from collections.abc import Callable
from pathlib import Path

from skill_scanner.schema import ScanResult, Verdict


class Unscannable(Exception):
    """Raised when a skill cannot be scanned (for example, a file is too large). The message says why."""


MAX_FILE_BYTES = 100 * 1024
MAX_FOLDER_BYTES = 500 * 1024


def is_junk(relative: Path) -> bool:
    """Files that are not part of the skill: macOS folder settings and git internals. Never shown, never checked."""
    return relative.name == ".DS_Store" or ".git" in relative.parts


def skill_paths(folder: Path):
    """Every path in the skill folder (files, folders and symlinks), without the junk."""
    return [p for p in folder.rglob("*") if not is_junk(p.relative_to(folder))]


def check_folder(folder: Path) -> None:
    """Refuse a folder we should not hand to the model. Raises Unscannable, with the reason."""
    if folder.is_symlink():
        raise Unscannable(f"skill folder is a symlink: {folder}")
    if not folder.is_dir():
        raise Unscannable(f"skill folder not found: {folder}")
    try:
        _check_contents(folder)
    except OSError as problem:
        raise Unscannable(f"skill folder could not be read: {problem}")
    if not (folder / "SKILL.md").is_file():
        raise Unscannable("skill folder has no SKILL.md")


def _check_contents(folder: Path) -> None:
    for p in skill_paths(folder):
        if p.is_symlink():
            raise Unscannable(f"skill folder contains a symlink: {p.relative_to(folder).as_posix()}")
    for p in skill_paths(folder):
        if p.is_file():
            if p.stat().st_size > MAX_FILE_BYTES:
                raise Unscannable(f"file too large to be scanned: {p.relative_to(folder).as_posix()}")
            try:
                p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                raise Unscannable(f"file cannot be read as text: {p.relative_to(folder).as_posix()}")
    total = sum(p.stat().st_size for p in skill_paths(folder) if p.is_file())
    if total > MAX_FOLDER_BYTES:
        raise Unscannable(f"skill folder too large to be scanned: {total} bytes, limit {MAX_FOLDER_BYTES}")


def scan(path: str, analyze: Callable[[str], Verdict]) -> ScanResult:
    """Scan one skill. `analyze` is the model: it takes the skill path and returns a Verdict.

    If `analyze` raises Unscannable, the result is marked unscannable. It is never reported as benign.
    """
    folder = Path(path).parent if Path(path).name == "SKILL.md" else Path(path)
    try:
        check_folder(folder)
        return ScanResult(status="scanned", verdict=analyze(str(folder)))
    except Unscannable as reason:
        return ScanResult(status="unscannable", error=str(reason))
