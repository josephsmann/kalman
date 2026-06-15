from __future__ import annotations

import json
from pathlib import Path

from .models import Document


def save(path, document: Document) -> None:
    Path(path).write_text(json.dumps(document.to_dict(), indent=2))


def load(path) -> Document:
    try:
        data = json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Not valid JSON: {e}") from e
    if not isinstance(data, dict) or "cells" not in data:
        raise ValueError("File is not a valid SolveIt document (missing 'cells').")
    return Document.from_dict(data)


def export_markdown(document: Document) -> str:
    blocks: list[str] = []
    for cell in document.cells:
        if cell.type == "note":
            blocks.append(cell.source)
        elif cell.type == "code":
            block = f"```python\n{cell.source}\n```"
            if cell.output:
                out = cell.output
                if out.error:
                    block += f"\n\n```\n{out.error}\n```"
                else:
                    body = "\n".join(p for p in (out.stdout.rstrip("\n"), out.result_repr) if p)
                    if body:
                        block += f"\n\n```\n{body}\n```"
            blocks.append(block)
        elif cell.type == "prompt":
            blocks.append(f"**Prompt:** {cell.source}")
        elif cell.type == "ai":
            blocks.append(f"**AI:** {cell.source}")
    return "\n\n".join(blocks) + "\n"
