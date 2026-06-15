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
    assert cell["output"] is None


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


def test_send_prompt_surfaces_llm_error():
    from solveit_widget.llm import LLMClient

    class BoomClient(LLMClient):
        def complete(self, messages):
            raise RuntimeError("boom")

    w = SolveItWidget(llm=BoomClient())
    p = w.add_cell("prompt")
    w.edit_cell(p, "hi")
    w.send_prompt(p)
    cells = _doc(w)["cells"]
    assert cells[-1]["type"] == "ai"
    assert "LLM error" in cells[-1]["source"]
    assert "boom" in cells[-1]["source"]


def test_token_count_includes_rendered_output():
    w = make_widget()
    a = w.add_cell("code")
    w.edit_cell(a, "print('x' * 200)")
    before = w.token_count
    w.run_cell(a)
    after = w.token_count
    assert after > before


def test_export_markdown_file(tmp_path):
    path = tmp_path / "doc.solveit.json"
    w = make_widget(path=str(path))
    n = w.add_cell("note")
    w.edit_cell(n, "hello notes")
    md_path = w.export_markdown_file()
    assert md_path is not None
    assert md_path.endswith(".md")
    import pathlib as _pl
    assert "hello notes" in _pl.Path(md_path).read_text()


def test_export_markdown_file_noop_without_path():
    w = make_widget()
    assert w.export_markdown_file() is None
