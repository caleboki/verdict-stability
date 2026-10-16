import inspect
import sys
from pathlib import Path
from types import SimpleNamespace

import anthropic
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import providers  # noqa: E402
from providers import TemperatureUnsupported, call_anthropic  # noqa: E402


class FakeBadRequest(Exception):
    pass


def fake_anthropic(monkeypatch, response=None, error=None):
    """Replace the Anthropic client with one that records the request."""
    sent = {}

    class FakeMessages:
        def create(self, **kwargs):
            sent.update(kwargs)
            if error:
                raise error
            return response

    class FakeClient:
        def __init__(self, **_):
            self.messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    monkeypatch.setattr(anthropic, "BadRequestError", FakeBadRequest)
    return sent


def response(*blocks):
    return SimpleNamespace(
        content=list(blocks), model="served", stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=10, output_tokens=50),
    )


TEXT = SimpleNamespace(type="text", text="Fine.\nScore: 40")
THINKING = SimpleNamespace(type="thinking", thinking="")


def test_every_argument_sent_exists_in_the_installed_sdk(monkeypatch):
    # The 1.x SDK dropped `temperature` from messages.create, which made every
    # temperature-0 call fail before reaching the API. Guard against that class of bug.
    sent = fake_anthropic(monkeypatch, response(TEXT))
    call_anthropic("m", "p", 0.0, 100)
    accepted = set(inspect.signature(anthropic.resources.Messages.create).parameters)
    assert set(sent) <= accepted


def test_temperature_goes_in_the_request_body(monkeypatch):
    sent = fake_anthropic(monkeypatch, response(TEXT))
    call_anthropic("m", "p", 0.0, 100)
    assert "temperature" not in sent and sent["extra_body"] == {"temperature": 0.0}


def test_default_condition_sends_no_temperature(monkeypatch):
    sent = fake_anthropic(monkeypatch, response(TEXT))
    call_anthropic("m", "p", None, 100)
    assert "temperature" not in sent and "extra_body" not in sent


def test_thinking_blocks_are_counted_but_not_kept(monkeypatch):
    fake_anthropic(monkeypatch, response(THINKING, TEXT))
    reply = call_anthropic("m", "p", None, 100)
    assert reply.text == "Fine.\nScore: 40" and reply.thinking_blocks == 1


def test_no_thinking_counts_zero(monkeypatch):
    fake_anthropic(monkeypatch, response(TEXT))
    assert call_anthropic("m", "p", None, 100).thinking_blocks == 0


def test_a_400_about_temperature_means_unsupported(monkeypatch):
    fake_anthropic(monkeypatch, error=FakeBadRequest("temperature: only the default value is allowed for this model"))
    with pytest.raises(TemperatureUnsupported):
        call_anthropic("m", "p", 0.0, 100)


def test_other_400s_are_not_mistaken_for_temperature(monkeypatch):
    fake_anthropic(monkeypatch, error=FakeBadRequest("model: not found"))
    with pytest.raises(FakeBadRequest):
        call_anthropic("m", "p", 0.0, 100)


def test_temperature_wording_does_not_matter():
    assert providers._looks_like_temperature_error(Exception("Unexpected value for 'temperature'"))
    assert not providers._looks_like_temperature_error(Exception("max_tokens too large"))
