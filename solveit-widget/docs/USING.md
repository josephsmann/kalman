# Using solveit-widget (standalone)

A practical guide to running the SolveIt-style dialog-engineering widget on your
own machine — no Claude Code, no special tooling. If you can run a marimo
notebook, you can run this.

The widget gives you one document where **executable code**, **markdown notes**,
and **editable AI dialogue** live together. The AI sees the whole document as
context, you build in small steps, and you can edit *any* message — including the
AI's — to reshape the conversation.

---

## 1. Prerequisites

- **Python 3.11+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (recommended) — manages the Python environment for you
- **Node.js 18+** — only needed once, to build the browser UI
- An **Anthropic API key** if you want the default Claude backend (optional — see [Without an API key](#6-without-an-api-key))

> Why uv? The widget ships as a Python package with a JavaScript frontend. uv
> creates an isolated environment with the right dependencies and runs marimo
> inside it, so you never fight version conflicts. You *can* use plain `pip` +
> `venv` instead (see [Alternative: pip](#appendix-a-install-with-pip-instead-of-uv)).

---

## 2. One-time setup

From the `solveit-widget/` directory:

```bash
# 1. Create the environment and install Python deps (incl. marimo)
uv sync --extra dev

# 2. Build the browser UI bundle (one time, requires Node)
cd frontend
npm install
npm run build
cd ..
```

That's it. The `npm run build` step produces `src/solveit_widget/static/index.js`,
the compiled Preact + CodeMirror interface. You only need to repeat it if you
change the frontend source.

---

## 3. Set your API key

The default backend is Anthropic's Claude. Provide a key via the environment:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Put it in your shell profile (`~/.zshrc`, `~/.bashrc`) to make it permanent, or
prefix individual commands with it. You can get a key from
<https://console.anthropic.com>.

If you'd rather not use Claude (or have no key), skip to
[Without an API key](#6-without-an-api-key).

---

## 4. Launch the demo notebook

```bash
uv run marimo edit demo.py
```

marimo starts a local server and opens your browser automatically. You'll see
the widget with a toolbar: **+ Code**, **+ Note**, **+ Prompt**, **Run all**,
**Save**, **Export .md**, and a live token counter.

To run on a specific port, or without a login token (useful for local dev):

```bash
uv run marimo edit demo.py --no-token -p 2718
```

Then open <http://localhost:2718> if it doesn't open on its own.

---

## 5. Using the widget

The interface is a vertical stack of **cells**. There are four kinds:

| Cell type | What it does |
|-----------|--------------|
| **Code** | Python you run in-place. Output (stdout, the last expression's value, errors, rich HTML) appears beneath it. |
| **Note** | Free-form markdown for your own reasoning and structure. |
| **Prompt** | A message *to* the AI. Pressing **Send** generates an AI reply below it. |
| **AI** | The model's response — and you can edit it like any other cell. |

### The core workflow

1. **Add a Code cell**, type a line or two, click **Run**. Output shows inline.
2. **Add a Note** to capture what you learned or what you're trying next.
3. **Add a Prompt**, ask the AI a question, click **Send**. The AI sees every
   *included* cell above — your code, its output, your notes — and replies in a
   new AI cell.
4. **Edit anything.** Change a code cell and re-run it. Or edit the AI's reply to
   fix a misunderstanding — that correction becomes part of the context the *next*
   prompt sees. This is the heart of "dialog engineering": you steer the
   conversation by editing it, not by starting over.
5. **Run all** resets the Python namespace and replays every code cell top to
   bottom — use it to get a clean, reproducible state.

### Per-cell controls

Each cell has a small control row:

- **↑ / ↓** — move the cell up or down.
- **ctx** checkbox — include or exclude this cell from what the AI sees. Untick
  long or irrelevant cells to save tokens; the **token counter** in the toolbar
  reflects roughly what your next prompt will send.
- **✕** — delete the cell.

### Editing never auto-runs

Editing a cell only changes its text. Code re-executes only when you click
**Run** (or **Run all**). Editing an AI or Note cell never runs anything — it
just reshapes context. This is deliberate: you stay in control of when code
executes.

### Saving and sharing

- **Save** writes the whole document to a JSON file (set via `path=`, see below).
  It also **autosaves** on every change, so you rarely need the button.
- **Export .md** writes a human-readable markdown version next to the JSON file
  (e.g. `session.solveit.json` → `session.solveit.md`) for sharing or reading.

---

## 6. Without an API key

The AI backend is pluggable. If you have no key, or want to test offline, pass a
`FakeClient` (returns a canned string) instead of the default Claude client.

You edit the widget construction in `demo.py` (or your own notebook). Change:

```python
widget = mo.ui.anywidget(SolveItWidget(path="my_session.solveit.json"))
```

to:

```python
from solveit_widget import FakeClient

widget = mo.ui.anywidget(
    SolveItWidget(path="my_session.solveit.json", llm=FakeClient("(no AI configured)"))
)
```

Everything else — code execution, notes, persistence, export — works fully
without a key. Only the **Send** action needs a real backend to be useful.

---

## 7. Using it in your own notebook

You don't have to use `demo.py`. In any marimo notebook (run via
`uv run marimo edit yournotebook.py`):

```python
import marimo as mo
from solveit_widget import SolveItWidget

widget = mo.ui.anywidget(SolveItWidget(path="my_project.solveit.json"))
widget
```

### Constructor options

```python
SolveItWidget(
    path=None,   # JSON file to load/save the document. If it exists, it's loaded.
                 # If None, the document lives only in memory (lost on restart).
    llm=None,    # An LLMClient. Defaults to ClaudeClient() (needs ANTHROPIC_API_KEY).
)
```

### Choosing a model or configuring Claude

```python
from solveit_widget import SolveItWidget, ClaudeClient

client = ClaudeClient(
    model="claude-sonnet-4-6",   # or another current Claude model
    api_key=None,                 # falls back to ANTHROPIC_API_KEY env var
    max_tokens=4096,
    system="You are a terse, code-first pair programmer.",  # optional system prompt
)

widget = mo.ui.anywidget(SolveItWidget(path="session.solveit.json", llm=client))
```

### Bringing your own backend

Any object implementing the `LLMClient` interface works — wire in OpenAI, a local
model, anything:

```python
from solveit_widget import LLMClient, SolveItWidget

class MyClient(LLMClient):
    def complete(self, messages: list[dict]) -> str:
        # messages is a list of {"role": "user"|"assistant", "content": str}
        # return the assistant's reply as a string
        ...

widget = mo.ui.anywidget(SolveItWidget(llm=MyClient()))
```

---

## 8. Running headless / on a remote machine

To run on a server and reach it from your laptop:

```bash
uv run marimo edit demo.py --headless --host 0.0.0.0 -p 2718
```

Then browse to `http://<server-ip>:2718`. Use marimo's token auth (omit
`--no-token`) or an SSH tunnel for anything beyond a trusted local network.

---

## 9. Security note

Code cells execute **in the same Python process** as the notebook, with no
sandbox. Anything you (or the AI, if you run its suggestions) put in a code cell
runs with your full permissions. Treat a SolveIt document like any script:
only run code you understand, and don't open untrusted `.solveit.json` files and
blindly hit **Run all**.

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'solveit_widget'` | marimo launched outside the project env | Always start with `uv run marimo edit ...` from `solveit-widget/`, not a global marimo. |
| `ModuleNotFoundError: No module named 'anthropic'` when sending a prompt | Default Claude client, deps missing | Run `uv sync --extra dev`; ensure you launched via `uv run`. |
| Widget shows "frontend not built yet" | The JS bundle wasn't built | Run `cd frontend && npm install && npm run build`. |
| Prompt returns `⚠ LLM error: Could not resolve authentication method...` | `ANTHROPIC_API_KEY` wasn't set in the shell that **launched** marimo | Export the key, then start marimo *in that same shell*: `export ANTHROPIC_API_KEY=sk-ant-...; uv run marimo edit demo.py`. Setting it after the server is running won't help — restart the server. |
| Prompt returns `⚠ LLM error: ...` (other) | Network or rate limit | The error text shows the cause; the document is never corrupted by an LLM failure. Just send again. |
| Editor doesn't show changes after **Run all** | Stale build | Rebuild the frontend (`npm run build`); recent versions sync editors to backend changes. |
| Port already in use | Another marimo on that port | Pick another port: `-p 2719`. |

---

## Appendix A: Install with pip instead of uv

If you don't use uv:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"     # installs the package + marimo + pytest
cd frontend && npm install && npm run build && cd ..
export ANTHROPIC_API_KEY="sk-ant-..."
marimo edit demo.py
```

## Appendix B: Run the tests

```bash
uv run pytest          # or: pytest, inside an activated venv
```

The Python core (models, executor, context assembly, persistence, LLM clients,
widget orchestration) is fully covered and runs without a browser or API key.
