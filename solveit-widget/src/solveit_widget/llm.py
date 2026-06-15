from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    def complete(self, messages: list[dict]) -> str:
        """Return the assistant's text reply for a list of {role, content} messages."""


class FakeClient(LLMClient):
    def __init__(self, response: str = "fake response") -> None:
        self.response = response
        self.last_messages: list[dict] | None = None

    def complete(self, messages: list[dict]) -> str:
        self.last_messages = messages
        return self.response


class ClaudeClient(LLMClient):
    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        api_key: str | None = None,
        max_tokens: int = 4096,
        system: str | None = None,
    ) -> None:
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.system = system

    def complete(self, messages: list[dict]) -> str:
        kwargs = dict(model=self.model, max_tokens=self.max_tokens, messages=messages)
        if self.system is not None:
            kwargs["system"] = self.system
        resp = self._client.messages.create(**kwargs)
        return "".join(b.text for b in resp.content if b.type == "text")
