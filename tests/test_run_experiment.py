import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import providers  # noqa: E402
import run_experiment  # noqa: E402
from providers import Reply, TemperatureUnsupported, is_retryable  # noqa: E402

MEAL = {"name": "fried chicken", "category": "clear_bad"}


class StatusError(Exception):
    def __init__(self, status_code):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


class GoogleStyleError(Exception):
    def __init__(self, code):
        super().__init__(f"code {code}")
        self.code = code


class APIConnectionError(Exception):
    pass


class ReadTimeout(Exception):
    pass


@pytest.mark.parametrize("exc, expected", [
    (StatusError(429), True),
    (StatusError(500), True),
    (StatusError(529), True),
    (GoogleStyleError(503), True),
    (APIConnectionError("reset"), True),
    (ReadTimeout("slow"), True),
    (StatusError(400), False),
    (StatusError(404), False),
    (GoogleStyleError(403), False),
    (KeyError("bug"), False),
])
def test_is_retryable(exc, expected):
    assert is_retryable(exc) is expected


def fake_provider(monkeypatch, behaviour):
    """Install a provider whose call runs behaviour(attempt) and count calls."""
    calls = []

    def call(model, prompt, temperature, max_tokens):
        calls.append(temperature)
        return behaviour(len(calls))

    monkeypatch.setitem(providers.PROVIDERS, "fake", (call, None))
    monkeypatch.setitem(run_experiment.PROVIDERS, "fake", (call, None))
    monkeypatch.setattr(run_experiment.time, "sleep", lambda s: None)
    return calls


def test_ok_answer_records_reply_details(monkeypatch):
    fake_provider(monkeypatch, lambda n: Reply("Fine.\nScore: 3", "served-1", "end_turn", 40, 25))
    rec = run_experiment.one_call("fake", "m", "default", MEAL, 0, "p", 100)
    assert rec["status"] == "ok" and rec["score"] == 3
    assert rec["served_model"] == "served-1" and rec["stop_reason"] == "end_turn"
    assert rec["input_tokens"] == 40 and rec["output_tokens"] == 25
    assert "error" not in rec


def test_answer_cut_off_at_max_tokens_is_truncated(monkeypatch):
    fake_provider(monkeypatch, lambda n: Reply("Long reasoning that never ends", stop_reason="max_tokens"))
    assert run_experiment.one_call("fake", "m", "default", MEAL, 0, "p", 100)["status"] == "truncated"


def test_unreadable_score_is_parse_failed(monkeypatch):
    fake_provider(monkeypatch, lambda n: Reply("Score: 6.5", stop_reason="end_turn"))
    rec = run_experiment.one_call("fake", "m", "default", MEAL, 0, "p", 100)
    assert rec["status"] == "parse_failed" and rec["score"] is None


def test_refusal_is_refused_not_parse_failed(monkeypatch):
    fake_provider(monkeypatch, lambda n: Reply("", stop_reason="refusal", output_tokens=0, refusal_category="cyber"))
    rec = run_experiment.one_call("fake", "m", "default", MEAL, 0, "p", 100)
    assert rec["status"] == "refused" and rec["score"] is None
    assert rec["refusal_category"] == "cyber"


def test_rate_limit_is_retried_until_it_succeeds(monkeypatch):
    def behaviour(n):
        if n < 3:
            raise StatusError(429)
        return Reply("Score: 2", stop_reason="end_turn")

    calls = fake_provider(monkeypatch, behaviour)
    rec = run_experiment.one_call("fake", "m", "default", MEAL, 0, "p", 100)
    assert len(calls) == 3 and rec["status"] == "ok" and rec["attempts"] == 3
    assert "error" not in rec


def test_bad_request_is_not_retried(monkeypatch):
    def behaviour(n):
        raise StatusError(404)

    calls = fake_provider(monkeypatch, behaviour)
    rec = run_experiment.one_call("fake", "m", "default", MEAL, 0, "p", 100)
    assert len(calls) == 1 and rec["status"] == "error" and "404" in rec["error"]


def test_server_errors_stop_after_max_attempts(monkeypatch):
    def behaviour(n):
        raise StatusError(503)

    calls = fake_provider(monkeypatch, behaviour)
    rec = run_experiment.one_call("fake", "m", "default", MEAL, 0, "p", 100)
    assert len(calls) == run_experiment.MAX_ATTEMPTS and rec["status"] == "error"


def test_rejected_temperature_is_recorded_once_without_retry(monkeypatch):
    def behaviour(n):
        raise TemperatureUnsupported("temperature is not supported")

    calls = fake_provider(monkeypatch, behaviour)
    rec = run_experiment.one_call("fake", "m", "t0", MEAL, 0, "p", 100)
    assert len(calls) == 1 and calls[0] == 0.0 and rec["status"] == "temperature_unsupported"


def test_read_progress_retries_errors_and_remembers_unsupported(tmp_path):
    rows = [
        {"provider": "a", "model": "m", "condition": "default", "meal": "x", "run": 0, "status": "ok"},
        {"provider": "a", "model": "m", "condition": "default", "meal": "x", "run": 1, "status": "error"},
        {"provider": "a", "model": "m", "condition": "default", "meal": "x", "run": 2, "status": "truncated"},
        {"provider": "a", "model": "m", "condition": "default", "meal": "x", "run": 3, "status": "refused"},
        {"provider": "a", "model": "m", "condition": "t0", "meal": "x", "run": 0, "status": "temperature_unsupported"},
    ]
    path = tmp_path / "raw.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    done, unsupported = run_experiment.read_progress(path)

    assert ("a", "m", "default", "x", 0) in done
    assert ("a", "m", "default", "x", 1) not in done
    assert ("a", "m", "default", "x", 2) in done
    assert ("a", "m", "default", "x", 3) in done
    assert unsupported == {("a", "m", "t0")}
