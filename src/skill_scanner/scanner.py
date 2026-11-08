"""Core scan logic. The model is passed in as a plain function, so nothing here depends on the agent framework."""

import contextvars
import os
import threading
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError

from skill_scanner.schema import ScanResult, Verdict


class Unscannable(Exception):
    """Raised when a skill cannot be scanned (for example, a file is too large). The message says why."""


MAX_FILE_BYTES = 100 * 1024
MAX_FOLDER_BYTES = 500 * 1024
DEFAULT_TIME_LIMIT_SECONDS = 120.0
DEFAULT_MAX_MODEL_CALLS = 20


class ModelCallBudget:
    """Counts model calls for one scan. The agent loop calls `use()` before each call, so a loop that keeps
    retrying a rejected answer is stopped instead of running up the bill."""

    def __init__(self, max_calls: int | None = None) -> None:
        self.max_calls = max_calls or int(os.getenv("SCANNER_MAX_MODEL_CALLS") or DEFAULT_MAX_MODEL_CALLS)
        self.used = 0

    def use(self) -> None:
        if self.used >= self.max_calls:
            raise Unscannable(f"scan hit the model call limit of {self.max_calls} calls")
        self.used += 1


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


def _run_with_time_limit(analyze: Callable[[str], Verdict], folder: str, seconds: float) -> Verdict:
    """Run `analyze` in a background thread and stop waiting after `seconds`.

    Python cannot kill a running thread. A stuck call is abandoned (a daemon thread, so it cannot block exit);
    the cap on model calls is what stops the spending. Errors from `analyze` are raised here, as if called directly.
    """
    outcome: dict = {}

    def work() -> None:
        try:
            outcome["verdict"] = analyze(folder)
        except BaseException as error:  # handed back to the caller below
            outcome["error"] = error

    thread = threading.Thread(target=contextvars.copy_context().run, args=(work,), daemon=True)
    thread.start()
    thread.join(seconds)
    if thread.is_alive():
        raise Unscannable(f"scan hit the time limit of {seconds:g} seconds")
    if "error" in outcome:
        raise outcome["error"]
    return outcome["verdict"]


def scan(path: str, analyze: Callable[[str], Verdict], time_limit_seconds: float | None = None) -> ScanResult:
    """Scan one skill. `analyze` is the model: it takes the skill path and returns a Verdict.

    If `analyze` raises Unscannable, the result is marked unscannable. It is never reported as benign.
    """
    folder = Path(path).parent if Path(path).name == "SKILL.md" else Path(path)
    try:
        check_folder(folder)
        seconds = time_limit_seconds or float(os.getenv("SCANNER_TIME_LIMIT_SECONDS") or DEFAULT_TIME_LIMIT_SECONDS)
        return ScanResult(status="scanned", verdict=_run_with_time_limit(analyze, str(folder), seconds))
    except Unscannable as reason:
        return ScanResult(status="unscannable", error=str(reason))
    except ValidationError as problem:
        return ScanResult(status="unscannable", error=f"the model gave an invalid answer: {problem.error_count()} problem(s)")
