import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from analyze import (  # noqa: E402
    generation_shift,
    latest_per_call,
    majority_vote_instability,
    output_prefix,
    per_meal,
    voting_table,
    wilson_interval,
)


def test_wilson_interval_known_value():
    lo, hi = wilson_interval(10, 20)
    assert lo == pytest.approx(0.299, abs=0.001)
    assert hi == pytest.approx(0.701, abs=0.001)


def test_wilson_interval_has_width_at_zero_and_n():
    lo, hi = wilson_interval(0, 20)
    assert lo == 0.0 and hi == pytest.approx(0.161, abs=0.001)
    lo, hi = wilson_interval(20, 20)
    assert hi == 1.0 and lo == pytest.approx(0.839, abs=0.001)


def test_per_meal_counts_flips_and_failures_separately():
    rows = [{"provider": "a", "model": "m", "condition": "default", "meal": "x", "category": "borderline",
             "status": "ok", "score": s} for s in (45, 49, 50, 60, 65)]
    rows += [{"provider": "a", "model": "m", "condition": "default", "meal": "x", "category": "borderline",
              "status": status, "score": None} for status in ("parse_failed", "truncated", "error")]

    row = per_meal(pd.DataFrame(rows), threshold=49.5).iloc[0]

    assert row["n"] == 5
    assert row["parse_failures"] == 1 and row["truncated"] == 1
    assert row["p_above"] == pytest.approx(0.6)
    assert row["verdict_instability"] == pytest.approx(0.4)
    assert row["p_above_lo"] < 0.6 < row["p_above_hi"]


def test_vote_of_one_is_single_run_instability():
    assert majority_vote_instability(0.3, 1) == pytest.approx(0.3)
    assert majority_vote_instability(0.8, 1) == pytest.approx(0.2)


def test_vote_of_three_known_value():
    # P(at least 2 of 3 above) at p = 0.3 is 3 * 0.09 * 0.7 + 0.027 = 0.216.
    assert majority_vote_instability(0.3, 3) == pytest.approx(0.216)


def test_voting_shrinks_noise_but_not_a_coin_flip():
    assert majority_vote_instability(0.2, 9) < majority_vote_instability(0.2, 3) < 0.2
    assert majority_vote_instability(0.5, 9) == pytest.approx(0.5)
    assert majority_vote_instability(0.0, 9) == 0.0


def test_vote_rejects_even_k():
    with pytest.raises(ValueError):
        majority_vote_instability(0.3, 4)


def _summary_row(model, meal, p_above, mean, category="borderline", condition="default"):
    return {"model": model, "condition": condition, "meal": meal, "category": category,
            "p_above": p_above, "mean": mean, "verdict_instability": min(p_above, 1 - p_above)}


def test_voting_table_has_one_column_per_k():
    summary = pd.DataFrame([_summary_row("m", "x", 0.3, 45), _summary_row("m", "y", 0.0, 10)])
    row = voting_table(summary, ks=(1, 3)).iloc[0]
    assert row["vote_of_1"] == pytest.approx(0.15)
    assert row["vote_of_3"] == pytest.approx(0.108)


def test_generation_shift_flags_a_crossed_verdict_only():
    summary = pd.DataFrame([
        _summary_row("old", "crossed", 0.1, 40), _summary_row("new", "crossed", 0.9, 60),
        _summary_row("old", "same", 0.9, 70), _summary_row("new", "same", 1.0, 80),
        _summary_row("old", "tied", 0.5, 50), _summary_row("new", "tied", 0.0, 30),
        _summary_row("old", "only_old", 0.0, 10),
    ])
    shift = generation_shift(summary, [["old", "new"]]).set_index("meal")

    assert set(shift.index) == {"crossed", "same", "tied"}
    assert shift.loc["crossed", "verdict_changed"]
    assert shift.loc["crossed", "mean_change"] == pytest.approx(20)
    assert not shift.loc["same", "verdict_changed"]
    assert not shift.loc["tied", "verdict_changed"]


def test_generation_shift_compares_within_a_condition():
    summary = pd.DataFrame([
        _summary_row("old", "x", 0.0, 10, condition="default"),
        _summary_row("new", "x", 1.0, 90, condition="t0"),
    ])
    assert generation_shift(summary, [["old", "new"]]).empty


def test_a_retried_call_replaces_its_earlier_error():
    key = {"provider": "a", "model": "m", "condition": "t0", "meal": "x"}
    df = pd.DataFrame([
        {**key, "run": 0, "timestamp": "2026-10-16T21:50:00", "status": "error"},
        {**key, "run": 1, "timestamp": "2026-10-16T21:50:01", "status": "error"},
        {**key, "run": 0, "timestamp": "2026-10-16T23:00:00", "status": "ok"},
    ])
    latest = latest_per_call(df).set_index("run")["status"]
    assert latest.to_dict() == {0: "ok", 1: "error"}


def test_errors_are_dropped_where_the_model_rejected_temperature():
    t0 = {"provider": "a", "model": "new", "condition": "t0", "meal": "x"}
    other = {"provider": "a", "model": "old", "condition": "t0", "meal": "x"}
    df = pd.DataFrame([
        {**t0, "run": 0, "timestamp": "2026-10-16T21:50:00", "status": "error"},
        {**t0, "run": 1, "timestamp": "2026-10-16T21:50:00", "status": "error"},
        {**t0, "run": 0, "timestamp": "2026-10-16T23:00:00", "status": "temperature_unsupported"},
        {**other, "run": 0, "timestamp": "2026-10-16T21:50:00", "status": "error"},
    ])
    latest = latest_per_call(df)
    assert sorted(latest["status"]) == ["error", "temperature_unsupported"]
    assert latest.loc[latest["status"] == "error", "model"].tolist() == ["old"]


@pytest.mark.parametrize("name, prefix", [
    ("raw.jsonl", ""),
    ("mock_raw.jsonl", "mock_"),
    ("monitor_raw.jsonl", "monitor_"),
    ("mock_monitor_raw.jsonl", "mock_monitor_"),
    ("other.jsonl", "other_"),
])
def test_output_prefix_keeps_tasks_apart(name, prefix):
    assert output_prefix(Path("results") / name) == prefix
