import pytest

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


def test_invalid_cell_type_raises():
    with pytest.raises(ValueError, match="type must be one of"):
        Cell(id="x", type="invalid")


def test_move_bad_direction_raises():
    d = Document()
    d.add(Cell(id="a", type="code"))
    with pytest.raises(ValueError, match="direction must be 'up' or 'down'"):
        d.move("a", "sideways")


def test_cell_output_from_dict_ignores_extra_keys():
    out = CellOutput.from_dict({"stdout": "hi", "unknown_key": "value"})
    assert out.stdout == "hi"
    assert out.stderr == ""


def test_roundtrip_to_from_dict():
    d = Document()
    d.add(Cell(id="a", type="code", source="x=1",
               output=CellOutput(stdout="hi", result_repr="1")))
    d.add(Cell(id="b", type="ai", source="hello", include_in_context=False))
    restored = Document.from_dict(d.to_dict())
    assert restored.to_dict() == d.to_dict()
    assert restored.get("a").output.stdout == "hi"
    assert restored.get("b").include_in_context is False
