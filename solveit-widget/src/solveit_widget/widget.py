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
        try:
            reply = self.llm.complete(messages)
        except Exception as exc:
            reply = f"⚠ LLM error: {exc}"
        index = self.document.index(cell_id) + 1
        ai_id = self._new_id()
        # Usage/cost is metadata, not dialog content — it stays out of context.
        usage = getattr(self.llm, "last_usage", None)
        metadata = {"usage": usage} if usage else {}
        self.document.add(
            Cell(id=ai_id, type="ai", source=reply, metadata=metadata), index=index
        )
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

    def export_markdown_file(self) -> str | None:
        if not self.path:
            return None
        md_path = str(pathlib.Path(self.path).with_suffix(".md"))
        pathlib.Path(md_path).write_text(self.export_markdown())
        return md_path

    def _new_id(self) -> str:
        return uuid.uuid4().hex

    def _sync(self) -> None:
        self.document_json = json.dumps(self.document.to_dict())
        self.token_count = self._estimate_tokens()
        self.save()

    def _estimate_tokens(self) -> int:
        msgs = []
        for c in self.document.cells:
            if not c.include_in_context:
                continue
            role = "assistant" if c.type == "ai" else "user"
            msgs.append({"role": role, "content": self.assembler.render_cell(c)})
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
        elif action == "export":
            self.export_markdown_file()
