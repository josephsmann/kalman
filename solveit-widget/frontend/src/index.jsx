import { h, Fragment, render as preactRender } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { EditorView, keymap } from "@codemirror/view";
import { EditorState } from "@codemirror/state";
import { defaultKeymap } from "@codemirror/commands";
import { python } from "@codemirror/lang-python";
import { marked } from "marked";
import markedKatex from "marked-katex-extension";

// Render $...$ and $$...$$ math via KaTeX. nonStandard lets `$x$` work without
// the surrounding-space rule. throwOnError keeps a bad formula from blanking the cell.
marked.use(markedKatex({ throwOnError: false, nonStandard: true }));

// KaTeX needs its stylesheet + fonts; pull from a pinned CDN (fonts can't be
// inlined cheaply). Injected once per document in render().
const KATEX_CSS = "https://cdn.jsdelivr.net/npm/katex@0.17.0/dist/katex.min.css";

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
  useEffect(() => {
    const view = viewRef.current;
    if (view && value !== view.state.doc.toString()) {
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: value || "" },
      });
    }
  }, [value]);
  return h("div", { ref, class: "sv-cm" });
}

function Output({ output }) {
  if (!output) return null;
  if (output.error) return h("pre", { class: "sv-out sv-err" }, output.error);
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
  useEffect(() => { setSrc(cell.source); }, [cell.source]);
  const commit = () => send(model, "edit", { id: cell.id, source: src });

  // Note/AI cells are markdown — default to rendered preview, toggle to edit.
  const markdownCell = cell.type === "note" || cell.type === "ai";
  const [preview, setPreview] = useState(markdownCell);

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
    markdownCell
      ? h("button", { onClick: () => setPreview(!preview) }, preview ? "Edit" : "Preview")
      : null,
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
  } else if (preview) {
    body = h("div", {
      class: "sv-md",
      onDblClick: () => setPreview(false),
      dangerouslySetInnerHTML: { __html: marked.parse(src || "") },
    });
  } else {
    body = h("textarea", {
      class: "sv-ta",
      value: src,
      onInput: (e) => setSrc(e.target.value),
      onBlur: commit,
    });
  }
  let footer = null;
  const usage = cell.metadata && cell.metadata.usage;
  if (cell.type === "ai" && usage) {
    const cost = usage.cost_usd != null ? `$${usage.cost_usd.toFixed(4)}` : "cost n/a";
    const label = `${usage.model} · ${usage.input_tokens} in / ${usage.output_tokens} out · ${cost}`;
    footer = h("div", { class: "sv-cost" }, label);
  }

  return h("div", { class: `sv-cell sv-${cell.type}` }, [controls, body, footer]);
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
    h("button", { onClick: () => send(model, "export") }, "Export .md"),
    h("span", { class: "sv-tokens" }, `~${tokens} tokens`),
  ]);

  const addBar = h("div", { class: "sv-toolbar sv-addbar" }, [
    h("button", { onClick: () => send(model, "add", { type: "code" }) }, "+ Code"),
    h("button", { onClick: () => send(model, "add", { type: "note" }) }, "+ Note"),
    h("button", { onClick: () => send(model, "add", { type: "prompt" }) }, "+ Prompt"),
  ]);

  return h("div", { class: "sv-app" }, [
    toolbar,
    ...doc.cells.map((c) => h(Cell, { key: c.id, model, cell: c })),
    addBar,
  ]);
}

const STYLE = `
.sv-app{font-family:system-ui;max-width:900px}
.sv-toolbar{display:flex;gap:6px;align-items:center;margin-bottom:10px}
.sv-addbar{margin-top:10px;margin-bottom:0;padding-top:8px;border-top:1px solid #eee}
.sv-tokens{margin-left:auto;color:#888;font-size:12px}
.sv-cell{border:1px solid #ddd;border-radius:6px;padding:8px;margin-bottom:8px}
.sv-controls{display:flex;gap:6px;align-items:center;font-size:12px;color:#666;margin-bottom:4px}
.sv-type{font-weight:600;text-transform:uppercase}
.sv-cm{border:1px solid #eee;border-radius:4px}
.sv-ta{width:100%;min-height:48px;font-family:inherit}
.sv-out{background:#f6f8fa;padding:6px;border-radius:4px;white-space:pre-wrap;margin-top:4px}
.sv-err{background:#fff0f0;color:#b00}
.sv-ai{background:#f7f9ff}
.sv-cost{margin-top:6px;font-size:11px;color:#999;font-family:ui-monospace,monospace}
.sv-md{padding:4px 2px;line-height:1.5}
.sv-md h1,.sv-md h2,.sv-md h3{margin:.4em 0 .2em}
.sv-md pre{background:#f6f8fa;padding:8px;border-radius:4px;overflow:auto}
.sv-md code{background:#f0f1f3;padding:1px 4px;border-radius:3px}
.sv-md pre code{background:none;padding:0}
.sv-md p{margin:.4em 0}
`;

function render({ model, el }) {
  // Inject the KaTeX stylesheet once per document (idempotent across cells).
  if (!document.getElementById("sv-katex-css")) {
    const link = document.createElement("link");
    link.id = "sv-katex-css";
    link.rel = "stylesheet";
    link.href = KATEX_CSS;
    document.head.appendChild(link);
  }
  const style = document.createElement("style");
  style.textContent = STYLE;
  el.appendChild(style);
  const root = document.createElement("div");
  el.appendChild(root);
  preactRender(h(App, { model }), root);
}

export default { render };
