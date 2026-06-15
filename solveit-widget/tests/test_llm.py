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
