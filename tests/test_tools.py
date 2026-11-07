import json

import pytest

from skill_scanner.scanner import Unscannable

from skill_scanner.tools import ToolRefused, list_files, read_file


def test_reading_a_path_that_escapes_the_skill_folder_is_refused(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("hello\n")
    (tmp_path / "secret.txt").write_text("top secret\n")

    with pytest.raises(ToolRefused):
        read_file(str(skill), "../secret.txt")


def test_reading_a_file_gives_one_json_object_per_line(tmp_path):
    (tmp_path / "SKILL.md").write_text("first\nsecond\n")

    out = read_file(str(tmp_path), "SKILL.md")

    assert [json.loads(row) for row in out.splitlines()] == [
        {"line": 1, "text": "first"},
        {"line": 2, "text": "second"},
    ]


def test_listing_shows_every_file_with_its_path_inside_the_skill_folder(tmp_path):
    (tmp_path / "SKILL.md").write_text("x")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "run.sh").write_text("echo hi")

    assert list_files(str(tmp_path)) == ["SKILL.md", "scripts/run.sh"]


def test_a_file_over_100_kb_is_too_large_to_be_scanned(tmp_path):
    (tmp_path / "big.sh").write_text("a" * (100 * 1024 + 1))

    with pytest.raises(Unscannable, match="too large to be scanned: big.sh"):
        read_file(str(tmp_path), "big.sh")


def test_reading_a_symlink_is_refused(tmp_path):
    skill = tmp_path / "skill"
    skill.mkdir()
    (tmp_path / "secret.txt").write_text("top secret\n")
    (skill / "link.txt").symlink_to(tmp_path / "secret.txt")

    with pytest.raises(ToolRefused, match="symlink"):
        read_file(str(skill), "link.txt")


def test_line_numbers_match_an_editor_even_with_odd_characters_inside_a_line(tmp_path):
    (tmp_path / "SKILL.md").write_text("a\x0bb\x0cc d\nsecond\n", encoding="utf-8")

    rows = [json.loads(r) for r in read_file(str(tmp_path), "SKILL.md").splitlines()]

    assert [r["line"] for r in rows] == [1, 2]
    assert rows[1]["text"] == "second"


def test_listing_hides_mac_and_git_junk(tmp_path):
    (tmp_path / "SKILL.md").write_text("x")
    (tmp_path / ".DS_Store").write_bytes(b"\xff")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref")

    assert list_files(str(tmp_path)) == ["SKILL.md"]


@pytest.mark.parametrize("path", ["nope.sh", "scripts"], ids=["missing-file", "a-folder"])
def test_asking_for_a_file_that_does_not_exist_is_refused_politely(tmp_path, path):
    (tmp_path / "scripts").mkdir()

    with pytest.raises(ToolRefused, match="not a file"):
        read_file(str(tmp_path), path)
