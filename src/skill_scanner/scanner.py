"""Core scan logic. The model is passed in as a plain function, so nothing here depends on the agent framework."""

from collections.abc import Callable

from skill_scanner.schema import ScanResult, Verdict


class Unscannable(Exception):
    """Raised when a skill cannot be scanned (for example, a file is too large). The message says why."""


def scan(path: str, analyze: Callable[[str], Verdict]) -> ScanResult:
    """Scan one skill. `analyze` is the model: it takes the skill path and returns a Verdict.

    If `analyze` raises Unscannable, the result is marked unscannable. It is never reported as benign.
    """
    try:
        return ScanResult(status="scanned", verdict=analyze(path))
    except Unscannable as reason:
        return ScanResult(status="unscannable", error=str(reason))
