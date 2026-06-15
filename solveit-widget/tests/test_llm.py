from solveit_widget.llm import FakeClient, LLMClient


def test_fake_client_is_llmclient():
    assert isinstance(FakeClient(), LLMClient)


def test_fake_client_returns_configured_response():
    c = FakeClient(response="canned")
    assert c.complete([{"role": "user", "content": "hi"}]) == "canned"


def test_fake_client_records_last_messages():
    c = FakeClient()
    msgs = [{"role": "user", "content": "hi"}]
    c.complete(msgs)
    assert c.last_messages == msgs


def test_abstract_client_cannot_instantiate():
    import pytest

    with pytest.raises(TypeError):
        LLMClient()


from unittest.mock import MagicMock, patch
from types import SimpleNamespace


def _fake_response(*texts, input_tokens=10, output_tokens=20):
    blocks = [SimpleNamespace(type="text", text=t) for t in texts]
    usage = SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens)
    return SimpleNamespace(content=blocks, usage=usage)


def test_estimate_cost_known_model():
    from solveit_widget.llm import estimate_cost

    assert estimate_cost("claude-sonnet-4-6", 1_000_000, 1_000_000) == 18.0


def test_estimate_cost_unknown_model_is_none():
    from solveit_widget.llm import estimate_cost

    assert estimate_cost("nope", 100, 100) is None


def test_claude_client_records_usage_and_cost():
    from solveit_widget.llm import ClaudeClient
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = _fake_response(
            "hi", input_tokens=1000, output_tokens=2000
        )
        client = ClaudeClient(model="claude-sonnet-4-6", api_key="x")
        client.complete([{"role": "user", "content": "hi"}])
        u = client.last_usage
        assert u["input_tokens"] == 1000
        assert u["output_tokens"] == 2000
        # 1000/1e6*3 + 2000/1e6*15 = 0.003 + 0.03 = 0.033
        assert abs(u["cost_usd"] - 0.033) < 1e-9


def test_claude_client_concatenates_and_forwards_kwargs():
    from solveit_widget.llm import ClaudeClient
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = _fake_response("Hello ", "world")
        client = ClaudeClient(model="claude-sonnet-4-6", api_key="x", max_tokens=123)
        out = client.complete([{"role": "user", "content": "hi"}])
        assert out == "Hello world"
        kwargs = instance.messages.create.call_args.kwargs
        assert kwargs["model"] == "claude-sonnet-4-6"
        assert kwargs["max_tokens"] == 123
        assert "system" not in kwargs


def test_claude_client_includes_system_when_set():
    from solveit_widget.llm import ClaudeClient
    with patch("anthropic.Anthropic") as MockAnthropic:
        instance = MockAnthropic.return_value
        instance.messages.create.return_value = _fake_response("ok")
        client = ClaudeClient(api_key="x", system="be terse")
        client.complete([{"role": "user", "content": "hi"}])
        assert instance.messages.create.call_args.kwargs["system"] == "be terse"
