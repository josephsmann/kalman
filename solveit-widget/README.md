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
