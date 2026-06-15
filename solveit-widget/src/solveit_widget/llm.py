from __future__ import annotations

from abc import ABC, abstractmethod

# USD per 1,000,000 tokens (input, output). Source: Claude API pricing.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-fable-5": (10.00, 50.00),
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """USD cost for a call, or None if the model's price is unknown."""
    price = MODEL_PRICING.get(model)
    if price is None:
        return None
    in_per_m, out_per_m = price
    return input_tokens / 1_000_000 * in_per_m + output_tokens / 1_000_000 * out_per_m


class LLMClient(ABC):
    @abstractmethod
    def complete(self, messages: list[dict]) -> str:
        """Return the assistant's text reply for a list of {role, content} messages."""


class FakeClient(LLMClient):
    def __init__(self, response: str = "fake response") -> None:
        self.response = response
        self.last_messages: list[dict] | None = None
        self.last_usage: dict | None = None

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
        self.last_usage: dict | None = None

    def complete(self, messages: list[dict]) -> str:
        kwargs = dict(model=self.model, max_tokens=self.max_tokens, messages=messages)
        if self.system is not None:
            kwargs["system"] = self.system
        resp = self._client.messages.create(**kwargs)
        in_tokens = getattr(resp.usage, "input_tokens", 0)
        out_tokens = getattr(resp.usage, "output_tokens", 0)
        self.last_usage = {
            "model": self.model,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "cost_usd": estimate_cost(self.model, in_tokens, out_tokens),
        }
        return "".join(b.text for b in resp.content if b.type == "text")
