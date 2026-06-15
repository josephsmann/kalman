# SolveIt-style anywidget — Design Spec

**Date:** 2026-06-15
**Status:** Approved (design), pending implementation plan

## Goal

Build a reusable [anywidget](https://anywidget.dev) package that emulates the
"faithful" core of Jeremy Howard / Answer.AI's **SolveIt** — a single coherent
document where executable code, markdown notes, and AI dialogue co-exist, every
message is editable (including the AI's), and the AI sees the whole document as
context. The widget is droppable into any marimo notebook.

This re-implements a small linear notebook *inside one widget* because marimo's
reactive DAG does not match SolveIt's linear append-and-run model.

## Key decisions (from brainstorming)

1. **Home:** reusable standalone `uv` package, `solveit-widget/`, with `pyproject.toml`.
2. **LLM backend:** pluggable `LLMClient` interface; ship a concrete `ClaudeClient`
   (Anthropic SDK) as the default plus a `FakeClient` for tests.
3. **Code execution:** in-process `exec` against a persistent namespace the widget
   owns, capturing stdout/stderr/last-expression (incl. rich reprs).
4. **Edit/replay semantics:** edit-in-place, **no auto re-run**. Code re-executes only
   on explicit run; editing an AI turn just reshapes future context. A manual
   "Run all" resets the namespace and replays code cells top-to-bottom.
5. **Context assembly:** full document every prompt — all *included* cells above the
   prompt (source + outputs + notes + prior AI turns) in order. Live token counter +
   per-cell include/exclude toggle as the pressure valve.
6. **Persistence:** JSON file is canonical state (load/save + autosave). One-way
   markdown export for sharing/reading.
7. **Frontend tooling:** Preact + CodeMirror 6, bundled with esbuild into a single
   `_esm` module.

## Architecture overview

A `uv` package `solveit-widget/` exposing `SolveItWidget(anywidget.AnyWidget)`.
The widget owns:

- a **Document model** (ordered cells) synced to the browser via traitlets,
- an **Executor** (persistent `globals` namespace, `exec` + output capture),
- an **LLMClient** (Claude default) for prompt cells,
- a **ContextAssembler** (serializes the document into LLM messages),
- a **Store** (JSON load/save + markdown export).

The frontend is a Preact + CodeMirror 6 app bundled by esbuild into a single ESM
file. State flows Python⇄JS over traitlets; actions (run cell, send prompt, edit,
add/delete/move) flow JS→Python as custom messages.

## Components & boundaries

Each module has one clear purpose, a defined interface, and is independently testable.

### `models.py` — pure data
- `Cell`: `id`, `type` ∈ {`code`, `note`, `prompt`, `ai`}, `source`, `output`
  (nullable `CellOutput`), `include_in_context: bool = True`, `metadata: dict`.
- `CellOutput`: `stdout`, `stderr`, `result_repr`, `result_html` (optional), `error`
  (optional traceback string).
- `Document`: ordered list of cells + helpers (`add`, `delete`, `move`, `cells_above`,
  `to_dict`/`from_dict`).
- No widget, execution, or LLM knowledge.

### `executor.py` — code execution
- `Executor.run(source: str) -> CellOutput`: runs against a persistent namespace
  (`self.ns: dict`); captures stdout/stderr; evaluates the last expression and
  records its repr, preferring `_repr_html_` when present; captures exceptions as a
  formatted traceback in `CellOutput.error` (never raises to the caller).
- `Executor.reset()`: fresh namespace (used by "Run all").
- No widget or LLM knowledge.

### `llm.py` — model access
- `LLMClient` (abstract): `complete(messages: list[dict]) -> str`.
- `ClaudeClient(LLMClient)`: Anthropic SDK; configurable `model` (default a current
  Claude, e.g. `claude-sonnet-4-6`) and API key (env `ANTHROPIC_API_KEY`).
- `FakeClient(LLMClient)`: deterministic, for tests.

### `context.py` — context assembly
- `ContextAssembler.build(document, upto_cell_id) -> list[dict]`: serializes all
  *included* cells positioned above the target prompt cell, in order
  (code source + captured output, notes, prior AI turns), into LLM messages.
- `ContextAssembler.count_tokens(messages) -> int`: token estimate for the live counter.
- Pure; no I/O.

### `store.py` — persistence
- `load(path) -> Document` / `save(path, document)`: JSON round-trip; validates schema
  and surfaces a clear error on malformed/old files (never silent data loss).
- `export_markdown(document) -> str`: one-way literate markdown.
- Pure file I/O.

### `widget.py` — orchestration (thin)
- `SolveItWidget`: traitlets for the serialized document + transient UI state;
  message handlers for `run`, `prompt`, `edit`, `add`, `delete`, `move`, `run_all`,
  `toggle_context`, `save`, `export`. Wires `Executor`, `LLMClient`, `ContextAssembler`,
  `Store`. No business logic beyond wiring.

### `frontend/` — UI
- Preact components: `App`, `CellList`, `CodeCell` (CodeMirror), `NoteCell`
  (markdown edit/preview), `PromptCell`, `AiCell` (editable), `Toolbar`
  (add cell, run all, save, export, token counter).
- esbuild bundles to `static/index.js`, referenced by the widget's `_esm`.

## Data flow

- **Run code cell:** JS `{action:"run", id}` → `Executor.run` → update cell output
  trait → JS renders inline output.
- **Send prompt:** JS `{action:"prompt", id}` → `ContextAssembler.build` over included
  cells above → `LLMClient.complete` → insert a new `ai` cell after the prompt → sync
  back. Token count shown live.
- **Edit any cell (incl. `ai`):** JS edits source → trait update → **no execution**;
  only changes future context. "Run all" → `Executor.reset()` then replay code cells
  top-to-bottom.
- **Persistence:** autosave + manual save to JSON; "Export markdown" yields a `.md`.

## Error handling

- Code exceptions → captured traceback in `CellOutput.error`, cell marked errored;
  widget never crashes.
- LLM errors → error banner on the prompt cell with retry; document untouched.
- Malformed/old JSON on load → validation error with a clear message; no silent loss.

## Testing

Python core is the priority and is fully unit-testable without a browser
(`uv run pytest`):

- `models`: construction, ordering, `to_dict`/`from_dict` round-trip.
- `executor`: run/capture stdout+result, rich repr, error capture, `reset`.
- `context`: ordering, include/exclude filtering, `upto` boundary, token count.
- `store`: JSON round-trip, malformed-file error, markdown export.
- `llm`: `FakeClient` drives prompt flow deterministically.
- `widget`: light message-handler tests (run, prompt, edit, add/delete/move).

Frontend: an esbuild smoke build in CI; minimal component tests optional in v1.

## Scope (v1 / YAGNI)

**In v1:** the six core modules + widget + frontend; add / delete / **move up-down**
cells; run cell; run all; send prompt; edit any cell; include/exclude toggle; token
counter; JSON save/load + autosave; markdown export; Claude + Fake clients.

**Deferred (not v1):** drag-and-drop reordering (move up/down is enough); subprocess
Jupyter kernel execution (the `Executor` interface leaves room to swap it in);
live namespace-state summary in context; windowed/truncated context; additional
concrete `LLMClient` providers; rich frontend test suite.
