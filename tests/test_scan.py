import threading

import pytest

from skill_scanner.scanner import ModelCallBudget, Unscannable, scan
from skill_scanner.schema import ScanResult, Verdict

BENIGN = Verdict(verdict="benign", category=None, confidence=0.9, evidence=[], reasoning="Formats commit messages.")


def test_a_normal_scan_returns_the_verdict_marked_as_scanned(tmp_path):
    (tmp_path / "SKILL.md").write_text("hi")
    result = scan(str(tmp_path), analyze=lambda path: BENIGN)

    assert result.status == "scanned"
    assert result.verdict == BENIGN
    assert result.error is None


def test_a_skill_that_cannot_be_scanned_is_marked_unscannable_with_no_verdict(tmp_path):
    (tmp_path / "SKILL.md").write_text("hi")
    def too_big(path):
        raise Unscannable("file too large to be scanned: big.sh")

    result = scan(str(tmp_path), analyze=too_big)

    assert result.status == "unscannable"
    assert result.verdict is None
    assert result.error == "file too large to be scanned: big.sh"


def test_the_printed_json_loads_back_into_the_same_result(tmp_path):
    (tmp_path / "SKILL.md").write_text("hi")
    result = scan(str(tmp_path), analyze=lambda path: BENIGN)

    assert ScanResult.model_validate_json(result.model_dump_json()) == result


class CountingModel:
    def __init__(self):
        self.calls = 0

    def __call__(self, path):
        self.calls += 1
        return BENIGN


def test_a_folder_over_500_kb_is_unscannable_and_the_model_is_never_called(tmp_path):
    for i in range(6):
        (tmp_path / f"part{i}.txt").write_text("a" * (90 * 1024))  # each file is fine, the folder is not
    model = CountingModel()

    result = scan(str(tmp_path), analyze=model)

    assert result.status == "unscannable"
    assert "too large to be scanned" in result.error
    assert model.calls == 0


def test_a_folder_containing_a_symlink_is_unscannable_and_the_model_is_never_called(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("hello")
    (tmp_path / "outside.txt").write_text("not part of the skill")
    (skill / "link.txt").symlink_to(tmp_path / "outside.txt")
    model = CountingModel()

    result = scan(str(skill), analyze=model)

    assert result.status == "unscannable"
    assert "symlink" in result.error
    assert model.calls == 0


def test_a_file_that_is_not_valid_text_makes_the_folder_unscannable_and_the_model_is_never_called(tmp_path):
    (tmp_path / "SKILL.md").write_text("hello")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")
    model = CountingModel()

    result = scan(str(tmp_path), analyze=model)

    assert result.status == "unscannable"
    assert "logo.png" in result.error
    assert model.calls == 0


def test_a_single_file_over_100_kb_is_unscannable_and_the_model_is_never_called(tmp_path):
    (tmp_path / "SKILL.md").write_text("hello")
    (tmp_path / "big.sh").write_text("a" * (100 * 1024 + 1))
    model = CountingModel()

    result = scan(str(tmp_path), analyze=model)

    assert result.status == "unscannable"
    assert "big.sh" in result.error
    assert model.calls == 0


def test_a_path_to_skill_md_scans_the_folder_it_is_in(tmp_path):
    (tmp_path / "SKILL.md").write_text("hello")
    seen = []

    def analyze(folder):
        seen.append(folder)
        return BENIGN

    scan(str(tmp_path / "SKILL.md"), analyze=analyze)

    assert seen == [str(tmp_path)]


def test_a_missing_folder_is_unscannable_and_the_model_is_never_called(tmp_path):
    model = CountingModel()

    result = scan(str(tmp_path / "typo"), analyze=model)

    assert result.status == "unscannable"
    assert "typo" in result.error
    assert model.calls == 0


def test_a_folder_without_a_skill_md_is_unscannable_and_the_model_is_never_called(tmp_path):
    (tmp_path / "notes.txt").write_text("hello")
    model = CountingModel()

    result = scan(str(tmp_path), analyze=model)

    assert result.status == "unscannable"
    assert "SKILL.md" in result.error
    assert model.calls == 0


def test_mac_and_git_junk_does_not_stop_a_skill_from_being_scanned(tmp_path):
    (tmp_path / "SKILL.md").write_text("hello")
    (tmp_path / ".DS_Store").write_bytes(b"\x00\x00\x00\x01Bud1\xff\xfe")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "index").write_bytes(b"\xff\xfe\x00\x01")
    model = CountingModel()

    result = scan(str(tmp_path), analyze=model)

    assert result.status == "scanned"
    assert model.calls == 1


def test_an_answer_that_fails_validation_ends_as_unscannable_not_a_crash(tmp_path):
    (tmp_path / "SKILL.md").write_text("hello")

    def bad_answer(folder):
        # A benign verdict with a category is not allowed, so this raises a ValidationError.
        return Verdict(verdict="benign", category="data-exfiltration", confidence=0.9, evidence=[], reasoning="x")

    result = scan(str(tmp_path), analyze=bad_answer)

    assert result.status == "unscannable"
    assert result.verdict is None
    assert "invalid answer" in result.error


def test_a_scan_that_takes_too_long_ends_as_unscannable_with_the_reason(tmp_path):
    (tmp_path / "SKILL.md").write_text("hello")
    release = threading.Event()

    def stalls(folder):
        release.wait(timeout=5)  # stands in for a model that never answers
        return BENIGN

    try:
        result = scan(str(tmp_path), analyze=stalls, time_limit_seconds=0.2)
    finally:
        release.set()

    assert result.status == "unscannable"
    assert result.verdict is None
    assert "time limit" in result.error


def test_the_model_call_budget_stops_a_loop_that_keeps_asking(tmp_path):
    budget = ModelCallBudget(max_calls=3)
    calls = 0

    with pytest.raises(Unscannable, match="model call limit"):
        while True:  # stands in for an agent that keeps retrying a rejected answer
            budget.use()
            calls += 1

    assert calls == 3
