from skill_scanner.scanner import Unscannable, scan
from skill_scanner.schema import ScanResult, Verdict

BENIGN = Verdict(verdict="benign", category=None, confidence=0.9, evidence=[], reasoning="Formats commit messages.")


def test_a_normal_scan_returns_the_verdict_marked_as_scanned():
    result = scan("some/skill/SKILL.md", analyze=lambda path: BENIGN)

    assert result.status == "scanned"
    assert result.verdict == BENIGN
    assert result.error is None


def test_a_skill_that_cannot_be_scanned_is_marked_unscannable_with_no_verdict():
    def too_big(path):
        raise Unscannable("file too large to be scanned: big.sh")

    result = scan("some/skill/SKILL.md", analyze=too_big)

    assert result.status == "unscannable"
    assert result.verdict is None
    assert result.error == "file too large to be scanned: big.sh"


def test_the_printed_json_loads_back_into_the_same_result():
    result = scan("some/skill/SKILL.md", analyze=lambda path: BENIGN)

    assert ScanResult.model_validate_json(result.model_dump_json()) == result
