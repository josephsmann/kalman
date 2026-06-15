# SolveIt-style anywidget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable anywidget package (`solveit-widget/`) that emulates the core of Answer.AI's SolveIt — one document where executable code, markdown notes, and editable AI dialogue co-exist, with the AI seeing the whole document as context.

**Architecture:** A `uv` package exposing `SolveItWidget(anywidget.AnyWidget)`. A pure-Python core (`models`, `executor`, `llm`, `context`, `store`) is wired by a thin `widget` orchestration layer to a Preact + CodeMirror 6 frontend bundled with esbuild. Code runs in-process via `exec` against a persistent namespace; edits never auto-run; context is the full document of included cells.

**Tech Stack:** Python 3.11+, `anywidget`, `traitlets`, `anthropic`, `pytest`, `uv`; Preact + CodeMirror 6 + esbuild (Node) for the frontend.

**Spec:** `docs/superpowers/specs/2026-06-15-solveit-widget-design.md`

---

## File Structure

```
solveit-widget/
  pyproject.toml
  README.md
  src/solveit_widget/
    __init__.py            # public exports
    models.py              # CellOutput, Cell, Document (pure data)
    executor.py            # Executor: exec + output capture
    llm.py                 # LLMClient, ClaudeClient, FakeClient
    context.py             # ContextAssembler: document -> messages
    store.py               # load/save JSON, export_markdown
    widget.py              # SolveItWidget orchestration
    static/index.js        # built frontend (esbuild output, gitignored optional)
  frontend/
    package.json
    build.mjs              # esbuild script
    src/index.jsx          # Preact app
  tests/
    test_models.py
    test_executor.py
    test_llm.py
    test_context.py
    test_store.py
    test_widget.py
  demo.py                  # marimo demo notebook
```

---

## Task 0: Scaffold the package

**Files:**
- Create: `solveit-widget/pyproject.toml`
- Create: `solveit-widget/src/solveit_widget/__init__.py` (empty for now)
- Create: `solveit-widget/.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "solveit-widget"
version = "0.1.0"
description = "A SolveIt-style dialog-engineering anywidget for marimo notebooks"
requires-python = ">=3.11"
dependencies = [
    "anywidget>=0.9",
    "traitlets>=5",
    "anthropic>=0.40",
]

[project.optional-dependencies]
dev = ["pytest>=8"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/solveit_widget"]
```

- [ ] **Step 2: Create empty `src/solveit_widget/__init__.py`**

```python
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
node_modules/
.venv/
```

- [ ] **Step 4: Verify the environment resolves**

Run: `cd solveit-widget && uv sync --extra dev`
Expected: a `.venv` is created and dependencies install without error.

- [ ] **Step 5: Commit**

```bash
git add solveit-widget/pyproject.toml solveit-widget/src/solveit_widget/__init__.py solveit-widget/.gitignore
git commit -m "chore: scaffold solveit-widget package"
```

---

## Task 1: Data models (`models.py`)

**Files:**
- Create: `solveit-widget/src/solveit_widget/models.py`
- Test: `solveit-widget/tests/test_models.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
from solveit_widget.models import Cell, CellOutput, Document


def test_cell_defaults():
    c = Cell(id="a", type="code")
    assert c.source == ""
    assert c.output is None
    assert c.include_in_context is True
    assert c.metadata == {}


def test_document_add_and_get():
    d = Document()
    d.add(Cell(id="a", type="code"))
    d.add(Cell(id="b", type="note"))
    assert [c.id for c in d.cells] == ["a", "b"]
    assert d.get("b").type == "note"


def test_document_add_at_index():
    d = Document()
    d.add(Cell(id="a", type="code"))
    d.add(Cell(id="b", type="code"), index=0)
    assert [c.id for c in d.cells] == ["b", "a"]


def test_document_delete():
    d = Document()
    d.add(Cell(id="a", type="code"))
    d.add(Cell(id="b", type="code"))
    d.delete("a")
    assert [c.id for c in d.cells] == ["b"]


def test_document_move():
    d = Document()
    for cid in ["a", "b", "c"]:
        d.add(Cell(id=cid, type="code"))
    d.move("c", "up")
    assert [c.id for c in d.cells] == ["a", "c", "b"]
    d.move("a", "down")
    assert [c.id for c in d.cells] == ["c", "a", "b"]
    d.move("c", "up")  # already at top, no-op
    assert [c.id for c in d.cells] == ["c", "a", "b"]


def test_cells_above_excludes_target_and_below():
    d = Document()
    for cid in ["a", "b", "c"]:
        d.add(Cell(id=cid, type="code"))
    assert [c.id for c in d.cells_above("c")] == ["a", "b"]
    assert [c.id for c in d.cells_above("a")] == []


def test_roundtrip_to_from_dict():
    d = Document()
    d.add(Cell(id="a", type="code", source="x=1",
               output=CellOutput(stdout="hi", result_repr="1")))
    d.add(Cell(id="b", type="ai", source="hello", include_in_context=False))
    restored = Document.from_dict(d.to_dict())
    assert restored.to_dict() == d.to_dict()
    assert restored.get("a").output.stdout == "hi"
    assert restored.get("b").include_in_context is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd solveit-widget && uv run pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solveit_widget.models'`

- [ ] **Step 3: Implement `models.py`**

```python
# src/solveit_widget/models.py
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CellOutput:
    stdout: str = ""
    stderr: str = ""
    result_repr: str = ""
    result_html: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "result_repr": self.result_repr,
            "result_html": self.result_html,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CellOutput":
        return cls(**d)


CELL_TYPES = ("code", "note", "prompt", "ai")


@dataclass
class Cell:
    id: str
    type: str
    source: str = ""
    output: CellOutput | None = None
    include_in_context: bool = True
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "output": self.output.to_dict() if self.output else None,
            "include_in_context": self.include_in_context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Cell":
        out = d.get("output")
        return cls(
            id=d["id"],
            type=d["type"],
            source=d.get("source", ""),
            output=CellOutput.from_dict(out) if out else None,
            include_in_context=d.get("include_in_context", True),
            metadata=d.get("metadata", {}),
        )


@dataclass
class Document:
    cells: list[Cell] = field(default_factory=list)

    def get(self, cell_id: str) -> Cell:
        for c in self.cells:
            if c.id == cell_id:
                return c
        raise KeyError(cell_id)

    def _index(self, cell_id: str) -> int:
        for i, c in enumerate(self.cells):
            if c.id == cell_id:
                return i
        raise KeyError(cell_id)

    def add(self, cell: Cell, index: int | None = None) -> None:
        if index is None:
            self.cells.append(cell)
        else:
            self.cells.insert(index, cell)

    def delete(self, cell_id: str) -> None:
        self.cells.pop(self._index(cell_id))

    def move(self, cell_id: str, direction: str) -> None:
        i = self._index(cell_id)
        j = i - 1 if direction == "up" else i + 1
        if 0 <= j < len(self.cells):
            self.cells[i], self.cells[j] = self.cells[j], self.cells[i]

    def cells_above(self, cell_id: str) -> list[Cell]:
        return self.cells[: self._index(cell_id)]

    def to_dict(self) -> dict:
        return {"cells": [c.to_dict() for c in self.cells]}

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        return cls(cells=[Cell.from_dict(c) for c in d.get("cells", [])])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd solveit-widget && uv run pytest tests/test_models.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add solveit-widget/src/solveit_widget/models.py solveit-widget/tests/test_models.py
git commit -m "feat: add document/cell data models"
```

---

## Task 2: Code executor (`executor.py`)

**Files:**
- Create: `solveit-widget/src/solveit_widget/executor.py`
- Test: `solveit-widget/tests/test_executor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_executor.py
from solveit_widget.executor import Executor


def test_captures_stdout():
    ex = Executor()
    out = ex.run("print('hello')")
    assert out.stdout.strip() == "hello"
    assert out.error is None


def test_last_expression_repr():
    ex = Executor()
    out = ex.run("1 + 2")
    assert out.result_repr == "3"


def test_no_result_for_statement():
    ex = Executor()
    out = ex.run("x = 5")
    assert out.result_repr == ""


def test_persistent_namespace():
    ex = Executor()
    ex.run("x = 41")
    out = ex.run("x + 1")
    assert out.result_repr == "42"


def test_error_is_captured_not_raised():
    ex = Executor()
    out = ex.run("1 / 0")
    assert out.error is not None
    assert "ZeroDivisionError" in out.error


def test_syntax_error_captured():
    ex = Executor()
    out = ex.run("def (")
    assert out.error is not None
    assert "SyntaxError" in out.error


def test_rich_html_repr():
    ex = Executor()
    src = (
        "class R:\n"
        "    def _repr_html_(self):\n"
        "        return '<b>hi</b>'\n"
        "R()"
    )
    out = ex.run(src)
    assert out.result_html == "<b>hi</b>"


def test_reset_clears_namespace():
    ex = Executor()
    ex.run("x = 1")
    ex.reset()
    out = ex.run("x")
    assert "NameError" in out.error
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd solveit-widget && uv run pytest tests/test_executor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solveit_widget.executor'`

- [ ] **Step 3: Implement `executor.py`**

```python
# src/solveit_widget/executor.py
from __future__ import annotations

import ast
import contextlib
import io
import traceback

from .models import CellOutput


class Executor:
    def __init__(self) -> None:
        self.ns: dict = {}

    def reset(self) -> None:
        self.ns = {}

    def run(self, source: str) -> CellOutput:
        out = CellOutput()
        try:
            tree = ast.parse(source)
        except SyntaxError:
            out.error = traceback.format_exc()
            return out

        last_expr = None
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = tree.body.pop()

        stdout, stderr = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exec(compile(tree, "<cell>", "exec"), self.ns)
                if last_expr is not None:
                    value = eval(
                        compile(ast.Expression(last_expr.value), "<cell>", "eval"),
                        self.ns,
                    )
                    if value is not None:
                        out.result_repr = repr(value)
                        html = getattr(value, "_repr_html_", None)
                        if callable(html):
                            try:
                                out.result_html = html()
                            except Exception:
                                out.result_html = None
        except Exception:
            out.error = traceback.format_exc()
        finally:
            out.stdout = stdout.getvalue()
            out.stderr = stderr.getvalue()
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd solveit-widget && uv run pytest tests/test_executor.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add solveit-widget/src/solveit_widget/executor.py solveit-widget/tests/test_executor.py
git commit -m "feat: add in-process code executor with output capture"
```

---

## Task 3: LLM clients (`llm.py`)

**Files:**
- Create: `solveit-widget/src/solveit_widget/llm.py`
- Test: `solveit-widget/tests/test_llm.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_llm.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd solveit-widget && uv run pytest tests/test_llm.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solveit_widget.llm'`

- [ ] **Step 3: Implement `llm.py`**

```python
# src/solveit_widget/llm.py
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
        if self.system:
            kwargs["system"] = self.system
        resp = self._client.messages.create(**kwargs)
        return "".join(b.text for b in resp.content if b.type == "text")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd solveit-widget && uv run pytest tests/test_llm.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add solveit-widget/src/solveit_widget/llm.py solveit-widget/tests/test_llm.py
git commit -m "feat: add pluggable LLM client interface with Claude and fake impls"
```

---

## Task 4: Context assembler (`context.py`)

**Files:**
- Create: `solveit-widget/src/solveit_widget/context.py`
- Test: `solveit-widget/tests/test_context.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_context.py
from solveit_widget.context import ContextAssembler
from solveit_widget.models import Cell, CellOutput, Document


def make_doc():
    d = Document()
    d.add(Cell(id="n", type="note", source="We are exploring data."))
    d.add(Cell(id="c", type="code", source="x = 1",
               output=CellOutput(stdout="ran", result_repr="1")))
    d.add(Cell(id="a", type="ai", source="Looks good."))
    d.add(Cell(id="p", type="prompt", source="What next?"))
    return d


def test_build_orders_cells_and_ends_with_prompt():
    msgs = ContextAssembler().build(make_doc(), "p")
    # last message is the prompt, role user
    assert msgs[-1]["role"] == "user"
    assert msgs[-1]["content"].endswith("What next?")


def test_ai_cell_becomes_assistant_message():
    msgs = ContextAssembler().build(make_doc(), "p")
    roles = [m["role"] for m in msgs]
    assert "assistant" in roles
    assert any(m["role"] == "assistant" and m["content"] == "Looks good." for m in msgs)


def test_code_cell_includes_source_and_output():
    msgs = ContextAssembler().build(make_doc(), "p")
    joined = "\n".join(m["content"] for m in msgs)
    assert "x = 1" in joined
    assert "ran" in joined


def test_excluded_cell_is_omitted():
    d = make_doc()
    d.get("c").include_in_context = False
    msgs = ContextAssembler().build(d, "p")
    joined = "\n".join(m["content"] for m in msgs)
    assert "x = 1" not in joined


def test_cells_below_prompt_excluded():
    d = make_doc()
    d.add(Cell(id="later", type="note", source="SHOULD NOT APPEAR"))
    msgs = ContextAssembler().build(d, "p")
    joined = "\n".join(m["content"] for m in msgs)
    assert "SHOULD NOT APPEAR" not in joined


def test_count_tokens_grows_with_content():
    asm = ContextAssembler()
    small = asm.count_tokens([{"role": "user", "content": "hi"}])
    big = asm.count_tokens([{"role": "user", "content": "hi" * 1000}])
    assert big > small
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd solveit-widget && uv run pytest tests/test_context.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solveit_widget.context'`

- [ ] **Step 3: Implement `context.py`**

```python
# src/solveit_widget/context.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd solveit-widget && uv run pytest tests/test_context.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add solveit-widget/src/solveit_widget/context.py solveit-widget/tests/test_context.py
git commit -m "feat: add context assembler turning the document into LLM messages"
```

---

## Task 5: Persistence (`store.py`)

**Files:**
- Create: `solveit-widget/src/solveit_widget/store.py`
- Test: `solveit-widget/tests/test_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_store.py
import pytest

from solveit_widget.models import Cell, CellOutput, Document
from solveit_widget.store import export_markdown, load, save


def test_save_load_roundtrip(tmp_path):
    d = Document()
    d.add(Cell(id="a", type="code", source="x=1",
               output=CellOutput(result_repr="1")))
    d.add(Cell(id="b", type="ai", source="hi"))
    path = tmp_path / "doc.json"
    save(path, d)
    restored = load(path)
    assert restored.to_dict() == d.to_dict()


def test_load_malformed_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"not_cells": []}')
    with pytest.raises(ValueError):
        load(path)


def test_load_invalid_json_raises(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json")
    with pytest.raises(ValueError):
        load(path)


def test_export_markdown_contains_all_types():
    d = Document()
    d.add(Cell(id="n", type="note", source="Some notes"))
    d.add(Cell(id="c", type="code", source="x = 1",
               output=CellOutput(stdout="ran")))
    d.add(Cell(id="p", type="prompt", source="What now?"))
    d.add(Cell(id="a", type="ai", source="Do this."))
    md = export_markdown(d)
    assert "Some notes" in md
    assert "```python" in md
    assert "x = 1" in md
    assert "What now?" in md
    assert "Do this." in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd solveit-widget && uv run pytest tests/test_store.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solveit_widget.store'`

- [ ] **Step 3: Implement `store.py`**

```python
# src/solveit_widget/store.py
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
                    body = (out.stdout + out.result_repr).strip()
                    if body:
                        block += f"\n\n```\n{body}\n```"
            blocks.append(block)
        elif cell.type == "prompt":
            blocks.append(f"**Prompt:** {cell.source}")
        elif cell.type == "ai":
            blocks.append(f"**AI:** {cell.source}")
    return "\n\n".join(blocks) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd solveit-widget && uv run pytest tests/test_store.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add solveit-widget/src/solveit_widget/store.py solveit-widget/tests/test_store.py
git commit -m "feat: add JSON persistence and markdown export"
```

---

## Task 6: Widget orchestration (`widget.py`)

The widget exposes public methods for every action (testable directly) plus a thin
`_handle` that maps frontend messages to those methods. `document_json` and
`token_count` are synced traits. `_new_id` uses `uuid4` (runtime only; tests pass
explicit ids by calling lower-level methods or asserting on generated structure).

**Files:**
- Create: `solveit-widget/src/solveit_widget/widget.py`
- Test: `solveit-widget/tests/test_widget.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_widget.py
import json

from solveit_widget.llm import FakeClient
from solveit_widget.models import Cell
from solveit_widget.widget import SolveItWidget


def make_widget(**kw):
    return SolveItWidget(llm=FakeClient(response="AI says hi"), **kw)


def _doc(w):
    return json.loads(w.document_json)


def test_starts_empty():
    w = make_widget()
    assert _doc(w)["cells"] == []


def test_add_cell_appends():
    w = make_widget()
    cid = w.add_cell("code")
    cells = _doc(w)["cells"]
    assert len(cells) == 1
    assert cells[0]["id"] == cid
    assert cells[0]["type"] == "code"


def test_edit_cell_updates_source_without_running():
    w = make_widget()
    cid = w.add_cell("code")
    w.edit_cell(cid, "y = 2")
    cell = _doc(w)["cells"][0]
    assert cell["source"] == "y = 2"
    assert cell["output"] is None  # editing does not execute


def test_run_cell_executes_and_stores_output():
    w = make_widget()
    cid = w.add_cell("code")
    w.edit_cell(cid, "print('hey')")
    w.run_cell(cid)
    assert _doc(w)["cells"][0]["output"]["stdout"].strip() == "hey"


def test_send_prompt_inserts_ai_cell_with_context():
    w = make_widget()
    code = w.add_cell("code")
    w.edit_cell(code, "x = 41")
    w.run_cell(code)
    prompt = w.add_cell("prompt")
    w.edit_cell(prompt, "what is x?")
    w.send_prompt(prompt)
    cells = _doc(w)["cells"]
    assert [c["type"] for c in cells] == ["code", "prompt", "ai"]
    assert cells[2]["source"] == "AI says hi"
    # the fake client saw the code context and the prompt
    sent = "\n".join(m["content"] for m in w.llm.last_messages)
    assert "x = 41" in sent
    assert "what is x?" in sent


def test_delete_and_move():
    w = make_widget()
    a = w.add_cell("code")
    b = w.add_cell("note")
    w.move_cell(b, "up")
    assert [c["id"] for c in _doc(w)["cells"]] == [b, a]
    w.delete_cell(a)
    assert [c["id"] for c in _doc(w)["cells"]] == [b]


def test_run_all_resets_namespace():
    w = make_widget()
    a = w.add_cell("code")
    w.edit_cell(a, "x = 5")
    w.run_cell(a)
    b = w.add_cell("code")
    w.edit_cell(b, "x + 1")
    w.run_all()
    assert _doc(w)["cells"][1]["output"]["result_repr"] == "6"


def test_toggle_context():
    w = make_widget()
    a = w.add_cell("code")
    w.toggle_context(a, False)
    assert _doc(w)["cells"][0]["include_in_context"] is False


def test_token_count_updates_on_change():
    w = make_widget()
    a = w.add_cell("note")
    w.edit_cell(a, "some text here")
    assert w.token_count > 0


def test_save_and_reopen(tmp_path):
    path = tmp_path / "doc.json"
    w = make_widget(path=str(path))
    a = w.add_cell("note")
    w.edit_cell(a, "persist me")
    w.save()
    w2 = make_widget(path=str(path))
    assert _doc(w2)["cells"][0]["source"] == "persist me"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd solveit-widget && uv run pytest tests/test_widget.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'solveit_widget.widget'`

- [ ] **Step 3: Implement `widget.py`**

```python
# src/solveit_widget/widget.py
from __future__ import annotations

import json
import pathlib
import uuid

import anywidget
import traitlets

from .context import ContextAssembler
from .executor import Executor
from .llm import ClaudeClient, LLMClient
from .models import Cell, Document
from .store import export_markdown, load, save

_STATIC = pathlib.Path(__file__).parent / "static"


class SolveItWidget(anywidget.AnyWidget):
    _esm = _STATIC / "index.js"

    document_json = traitlets.Unicode("{}").tag(sync=True)
    token_count = traitlets.Int(0).tag(sync=True)

    def __init__(self, path: str | None = None, llm: LLMClient | None = None, **kw):
        super().__init__(**kw)
        self.path = path
        self.executor = Executor()
        self.llm = llm or ClaudeClient()
        self.assembler = ContextAssembler()
        if path and pathlib.Path(path).exists():
            self.document = load(path)
        else:
            self.document = Document()
        self._sync()
        self.on_msg(self._handle)

    # ---- public actions -------------------------------------------------

    def add_cell(self, type: str, index: int | None = None) -> str:
        cid = self._new_id()
        self.document.add(Cell(id=cid, type=type), index=index)
        self._sync()
        return cid

    def edit_cell(self, cell_id: str, source: str) -> None:
        self.document.get(cell_id).source = source
        self._sync()

    def run_cell(self, cell_id: str) -> None:
        cell = self.document.get(cell_id)
        if cell.type == "code":
            cell.output = self.executor.run(cell.source)
        self._sync()

    def run_all(self) -> None:
        self.executor.reset()
        for cell in self.document.cells:
            if cell.type == "code":
                cell.output = self.executor.run(cell.source)
        self._sync()

    def send_prompt(self, cell_id: str) -> None:
        messages = self.assembler.build(self.document, cell_id)
        reply = self.llm.complete(messages)
        index = self.document._index(cell_id) + 1
        ai_id = self._new_id()
        self.document.add(Cell(id=ai_id, type="ai", source=reply), index=index)
        self._sync()

    def delete_cell(self, cell_id: str) -> None:
        self.document.delete(cell_id)
        self._sync()

    def move_cell(self, cell_id: str, direction: str) -> None:
        self.document.move(cell_id, direction)
        self._sync()

    def toggle_context(self, cell_id: str, value: bool) -> None:
        self.document.get(cell_id).include_in_context = value
        self._sync()

    def save(self) -> None:
        if self.path:
            save(self.path, self.document)

    def export_markdown(self) -> str:
        return export_markdown(self.document)

    # ---- internals ------------------------------------------------------

    def _new_id(self) -> str:
        return uuid.uuid4().hex

    def _sync(self) -> None:
        self.document_json = json.dumps(self.document.to_dict())
        self.token_count = self._estimate_tokens()
        self.save()

    def _estimate_tokens(self) -> int:
        msgs = [{"role": "user", "content": c.source} for c in self.document.cells
                if c.include_in_context]
        return self.assembler.count_tokens(msgs)

    def _handle(self, widget, content, buffers) -> None:
        action = content.get("action")
        if action == "add":
            self.add_cell(content["type"], content.get("index"))
        elif action == "edit":
            self.edit_cell(content["id"], content["source"])
        elif action == "run":
            self.run_cell(content["id"])
        elif action == "run_all":
            self.run_all()
        elif action == "prompt":
            self.edit_cell(content["id"], content["source"])
            self.send_prompt(content["id"])
        elif action == "delete":
            self.delete_cell(content["id"])
        elif action == "move":
            self.move_cell(content["id"], content["direction"])
        elif action == "toggle_context":
            self.toggle_context(content["id"], content["value"])
        elif action == "save":
            self.save()
```

Note: `test_save_and_reopen` works because `_sync` autosaves on every change; opening a
second widget with the same `path` loads it. `test_token_count_updates_on_change`
passes because `_estimate_tokens` counts included cell sources.

- [ ] **Step 4: Add a placeholder `static/index.js` so the widget imports**

The widget references `_STATIC / "index.js"`. Until Task 7 builds the real bundle,
create a minimal placeholder so `SolveItWidget` can be constructed in tests.

Create `solveit-widget/src/solveit_widget/static/index.js`:

```javascript
export function render({ model, el }) {
  el.textContent = "SolveItWidget (frontend not built yet)";
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd solveit-widget && uv run pytest tests/test_widget.py -v`
Expected: PASS (10 passed)

- [ ] **Step 6: Run the full suite**

Run: `cd solveit-widget && uv run pytest -v`
Expected: PASS (all tasks' tests green)

- [ ] **Step 7: Commit**

```bash
git add solveit-widget/src/solveit_widget/widget.py solveit-widget/tests/test_widget.py solveit-widget/src/solveit_widget/static/index.js
git commit -m "feat: add SolveItWidget orchestration layer"
```

---

## Task 7: Frontend (Preact + CodeMirror, esbuild)

This task produces the real `static/index.js`. It is validated by a **smoke build**
(esbuild must produce a non-empty bundle) rather than unit tests.

**Files:**
- Create: `solveit-widget/frontend/package.json`
- Create: `solveit-widget/frontend/build.mjs`
- Create: `solveit-widget/frontend/src/index.jsx`
- Output (overwrites placeholder): `solveit-widget/src/solveit_widget/static/index.js`

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "solveit-widget-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "node build.mjs"
  },
  "dependencies": {
    "preact": "^10.20.0",
    "htm": "^3.1.1",
    "@codemirror/state": "^6.4.0",
    "@codemirror/view": "^6.26.0",
    "@codemirror/lang-python": "^6.1.0",
    "codemirror": "^6.0.1"
  },
  "devDependencies": {
    "esbuild": "^0.20.0"
  }
}
```

- [ ] **Step 2: Create `frontend/build.mjs`**

```javascript
import * as esbuild from "esbuild";

await esbuild.build({
  entryPoints: ["src/index.jsx"],
  bundle: true,
  format: "esm",
  outfile: "../src/solveit_widget/static/index.js",
  minify: true,
  jsxFactory: "h",
  jsxFragment: "Fragment",
  loader: { ".jsx": "jsx" },
});

console.log("built static/index.js");
```

- [ ] **Step 3: Create `frontend/src/index.jsx`**

```jsx
import { h, Fragment, render as preactRender } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { EditorView, keymap } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { defaultKeymap } from "@codemirror/commands";
import { python } from "@codemirror/lang-python";

function send(model, action, extra = {}) {
  model.send({ action, ...extra });
}

function CodeMirrorBox({ value, onChange }) {
  const ref = useRef(null);
  const viewRef = useRef(null);
  useEffect(() => {
    const view = new EditorView({
      parent: ref.current,
      state: EditorState.create({
        doc: value || "",
        extensions: [
          python(),
          keymap.of(defaultKeymap),
          EditorView.updateListener.of((u) => {
            if (u.docChanged) onChange(u.state.doc.toString());
          }),
        ],
      }),
    });
    viewRef.current = view;
    return () => view.destroy();
  }, []);
  return h("div", { ref, class: "sv-cm" });
}

function Output({ output }) {
  if (!output) return null;
  if (output.error)
    return h("pre", { class: "sv-out sv-err" }, output.error);
  if (output.result_html)
    return h("div", {
      class: "sv-out",
      dangerouslySetInnerHTML: { __html: output.result_html },
    });
  const body = ((output.stdout || "") + (output.result_repr || "")).trim();
  return body ? h("pre", { class: "sv-out" }, body) : null;
}

function Cell({ model, cell }) {
  const [src, setSrc] = useState(cell.source);
  const commit = () => send(model, "edit", { id: cell.id, source: src });

  const controls = h("div", { class: "sv-controls" }, [
    h("span", { class: "sv-type" }, cell.type),
    h("button", { onClick: () => send(model, "move", { id: cell.id, direction: "up" }) }, "↑"),
    h("button", { onClick: () => send(model, "move", { id: cell.id, direction: "down" }) }, "↓"),
    h("label", {}, [
      h("input", {
        type: "checkbox",
        checked: cell.include_in_context,
        onChange: (e) =>
          send(model, "toggle_context", { id: cell.id, value: e.target.checked }),
      }),
      " ctx",
    ]),
    h("button", { onClick: () => send(model, "delete", { id: cell.id }) }, "✕"),
  ]);

  let body;
  if (cell.type === "code") {
    body = h(Fragment, {}, [
      h(CodeMirrorBox, { value: cell.source, onChange: setSrc }),
      h("button", { onClick: () => { commit(); send(model, "run", { id: cell.id }); } }, "Run"),
      h(Output, { output: cell.output }),
    ]);
  } else if (cell.type === "prompt") {
    body = h(Fragment, {}, [
      h("textarea", {
        class: "sv-ta",
        value: src,
        onInput: (e) => setSrc(e.target.value),
        placeholder: "Ask the AI…",
      }),
      h("button", { onClick: () => send(model, "prompt", { id: cell.id, source: src }) }, "Send"),
    ]);
  } else {
    // note or ai — editable text
    body = h("textarea", {
      class: "sv-ta",
      value: src,
      onInput: (e) => setSrc(e.target.value),
      onBlur: commit,
    });
  }
  return h("div", { class: `sv-cell sv-${cell.type}` }, [controls, body]);
}

function App({ model }) {
  const [doc, setDoc] = useState(JSON.parse(model.get("document_json")));
  const [tokens, setTokens] = useState(model.get("token_count"));

  useEffect(() => {
    const onDoc = () => setDoc(JSON.parse(model.get("document_json")));
    const onTok = () => setTokens(model.get("token_count"));
    model.on("change:document_json", onDoc);
    model.on("change:token_count", onTok);
    return () => {
      model.off("change:document_json", onDoc);
      model.off("change:token_count", onTok);
    };
  }, []);

  const toolbar = h("div", { class: "sv-toolbar" }, [
    h("button", { onClick: () => send(model, "add", { type: "code" }) }, "+ Code"),
    h("button", { onClick: () => send(model, "add", { type: "note" }) }, "+ Note"),
    h("button", { onClick: () => send(model, "add", { type: "prompt" }) }, "+ Prompt"),
    h("button", { onClick: () => send(model, "run_all") }, "Run all"),
    h("button", { onClick: () => send(model, "save") }, "Save"),
    h("span", { class: "sv-tokens" }, `~${tokens} tokens`),
  ]);

  return h("div", { class: "sv-app" }, [
    toolbar,
    ...doc.cells.map((c) => h(Cell, { key: c.id, model, cell: c })),
  ]);
}

const STYLE = `
.sv-app{font-family:system-ui;max-width:900px}
.sv-toolbar{display:flex;gap:6px;align-items:center;margin-bottom:10px}
.sv-tokens{margin-left:auto;color:#888;font-size:12px}
.sv-cell{border:1px solid #ddd;border-radius:6px;padding:8px;margin-bottom:8px}
.sv-controls{display:flex;gap:6px;align-items:center;font-size:12px;color:#666;margin-bottom:4px}
.sv-type{font-weight:600;text-transform:uppercase}
.sv-cm{border:1px solid #eee;border-radius:4px}
.sv-ta{width:100%;min-height:48px;font-family:inherit}
.sv-out{background:#f6f8fa;padding:6px;border-radius:4px;white-space:pre-wrap;margin-top:4px}
.sv-err{background:#fff0f0;color:#b00}
.sv-ai{background:#f7f9ff}
`;

export function render({ model, el }) {
  const style = document.createElement("style");
  style.textContent = STYLE;
  el.appendChild(style);
  const root = document.createElement("div");
  el.appendChild(root);
  preactRender(h(App, { model }), root);
}
```

- [ ] **Step 4: Install deps and build**

Run: `cd solveit-widget/frontend && npm install && npm run build`
Expected: prints `built static/index.js`; `../src/solveit_widget/static/index.js` exists and is non-empty.

- [ ] **Step 5: Smoke-check the bundle is non-trivial**

Run: `test -s solveit-widget/src/solveit_widget/static/index.js && echo OK`
Expected: `OK` (file exists and is non-empty, replacing the placeholder).

- [ ] **Step 6: Re-run the Python suite (widget still constructs)**

Run: `cd solveit-widget && uv run pytest -v`
Expected: PASS (all green; the real bundle does not affect Python tests).

- [ ] **Step 7: Commit**

```bash
git add solveit-widget/frontend solveit-widget/src/solveit_widget/static/index.js
git commit -m "feat: add Preact + CodeMirror frontend bundled with esbuild"
```

---

## Task 8: Public API, demo notebook, and README

**Files:**
- Modify: `solveit-widget/src/solveit_widget/__init__.py`
- Create: `solveit-widget/demo.py`
- Create: `solveit-widget/README.md`

- [ ] **Step 1: Write the failing test for public exports**

Create `solveit-widget/tests/test_api.py`:

```python
def test_public_exports():
    import solveit_widget as sw

    assert hasattr(sw, "SolveItWidget")
    assert hasattr(sw, "LLMClient")
    assert hasattr(sw, "ClaudeClient")
    assert hasattr(sw, "FakeClient")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd solveit-widget && uv run pytest tests/test_api.py -v`
Expected: FAIL (`AttributeError` / empty `__init__`)

- [ ] **Step 3: Fill in `__init__.py`**

```python
# src/solveit_widget/__init__.py
from .llm import ClaudeClient, FakeClient, LLMClient
from .widget import SolveItWidget

__all__ = ["SolveItWidget", "LLMClient", "ClaudeClient", "FakeClient"]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd solveit-widget && uv run pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Create `demo.py` (marimo notebook)**

```python
import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from solveit_widget import SolveItWidget

    return SolveItWidget, mo


@app.cell
def _(SolveItWidget, mo):
    widget = mo.ui.anywidget(SolveItWidget(path="my_session.solveit.json"))
    widget
    return (widget,)


if __name__ == "__main__":
    app.run()
```

- [ ] **Step 6: Create `README.md`**

```markdown
# solveit-widget

A SolveIt-style dialog-engineering anywidget for marimo notebooks: one document
where executable code, markdown notes, and editable AI dialogue co-exist, with the
AI seeing the whole document as context.

## Install

```bash
uv sync --extra dev
cd frontend && npm install && npm run build && cd ..
```

## Use (in marimo)

```python
import marimo as mo
from solveit_widget import SolveItWidget

mo.ui.anywidget(SolveItWidget(path="session.solveit.json"))
```

Set `ANTHROPIC_API_KEY` for the default Claude backend, or pass your own
`LLMClient` via `SolveItWidget(llm=...)`.

## Develop

```bash
uv run pytest                       # Python core tests
cd frontend && npm run build        # rebuild the UI bundle
```

## Architecture

See `../docs/superpowers/specs/2026-06-15-solveit-widget-design.md`.
```

- [ ] **Step 7: Run the full suite**

Run: `cd solveit-widget && uv run pytest -v`
Expected: PASS (all tests across all tasks).

- [ ] **Step 8: Commit**

```bash
git add solveit-widget/src/solveit_widget/__init__.py solveit-widget/demo.py solveit-widget/README.md solveit-widget/tests/test_api.py
git commit -m "feat: public API, demo notebook, and README"
```

---

## Done criteria

- `uv run pytest` is green across `models`, `executor`, `llm`, `context`, `store`, `widget`, `api`.
- `cd frontend && npm run build` produces a non-empty `static/index.js`.
- `uv run marimo edit demo.py` renders the widget; you can add code/note/prompt cells, run code, send a prompt (with `ANTHROPIC_API_KEY` set), edit any cell, toggle context, run all, and the session persists to JSON.
```
