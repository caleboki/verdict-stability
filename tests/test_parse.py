import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from parse import parse_score  # noqa: E402


def test_plain_final_line():
    assert parse_score("Lean protein, but mayo adds fat.\nScore: 62") == 62


def test_uses_last_score_when_several_appear():
    assert parse_score("Initially Score: 40 seems fair, but reconsidering.\nScore: 55") == 55


def test_markdown_bold_and_out_of_hundred():
    assert parse_score("**Score:** 70/100") == 70


def test_bold_number():
    assert parse_score("Score: **65**") == 65


def test_case_insensitive():
    assert parse_score("score: 100") == 100


def test_zero_is_a_valid_score():
    assert parse_score("Score: 0") == 0


def test_sentence_full_stop_after_score():
    assert parse_score("Reasonable choice overall. Score: 60.") == 60


def test_rejects_out_of_range():
    assert parse_score("Score: 101") is None
    assert parse_score("Score: 1000") is None


def test_missing_or_empty():
    assert parse_score("I would rate this fairly low.") is None
    assert parse_score("") is None
    assert parse_score(None) is None


@pytest.mark.parametrize("text", [
    "Score: 62.5",
    "Score: 62,5",
    "Score: 60-70",
    "Score: 60 - 70",
    "Score: 60–70",
    "Score: 60 to 70",
    "Score: 7/10",
    "**Score:** 7 / 10",
])
def test_decimal_range_or_out_of_ten_is_a_parse_failure(text):
    assert parse_score(text) is None


def test_final_decimal_does_not_fall_back_to_an_earlier_whole_number():
    assert parse_score("At first Score: 40 felt right.\nScore: 55.5") is None
