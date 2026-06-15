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
    h("button", { onClick: () => send(model, "export") }, "Export .md"),
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
