from __future__ import annotations

from .models import Cell, Document


class ContextAssembler:
    def build(self, document: Document, upto_cell_id: str) -> list[dict]:
        messages: list[dict] = []
        buffer: list[str] = []

        def flush() -> None:
            if buffer:
                messages.append({"role": "user", "content": "\n\n".join(buffer)})
                buffer.clear()

        for cell in document.cells_above(upto_cell_id):
            if not cell.include_in_context:
                continue
            if cell.type == "ai":
                flush()
                messages.append({"role": "assistant", "content": cell.source})
            else:
                buffer.append(self._render(cell))

        prompt = document.get(upto_cell_id)
        buffer.append(prompt.source)
        flush()
        return messages

    def _render(self, cell: Cell) -> str:
        if cell.type == "code":
            parts = [f"```python\n{cell.source}\n```"]
            if cell.output:
                out = cell.output
                if out.error:
                    parts.append(f"Error:\n```\n{out.error}\n```")
                else:
                    body = (out.stdout + ("\n" if out.stdout and out.result_repr else "")
                            + out.result_repr).strip()
                    if body:
                        parts.append(f"Output:\n```\n{body}\n```")
            return "\n".join(parts)
        return cell.source  # note / prompt

    def count_tokens(self, messages: list[dict]) -> int:
        chars = sum(len(m["content"]) for m in messages)
        return chars // 4
