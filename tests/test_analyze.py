import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from analyze import per_meal, wilson_interval  # noqa: E402


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
    assert row["p_suitable"] == pytest.approx(0.6)
    assert row["verdict_instability"] == pytest.approx(0.4)
    assert row["p_suitable_lo"] < 0.6 < row["p_suitable_hi"]
