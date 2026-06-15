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


def test_adjacent_ai_cells_produce_no_empty_user_message():
    d = Document()
    d.add(Cell(id="a1", type="ai", source="first"))
    d.add(Cell(id="a2", type="ai", source="second"))
    d.add(Cell(id="p", type="prompt", source="go"))
    msgs = ContextAssembler().build(d, "p")
    assert all(m["content"] != "" for m in msgs)
    assert [m["role"] for m in msgs] == ["assistant", "assistant", "user"]


def test_error_output_renders_error_label():
    d = Document()
    d.add(Cell(id="c", type="code", source="1/0",
               output=CellOutput(error="ZeroDivisionError: division by zero")))
    d.add(Cell(id="p", type="prompt", source="why?"))
    msgs = ContextAssembler().build(d, "p")
    joined = "\n".join(m["content"] for m in msgs)
    assert "Error:" in joined
    assert "ZeroDivisionError" in joined
