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


def test_export_markdown_separates_stdout_and_result():
    d = Document()
    d.add(Cell(id="c", type="code", source="print('hello'); 42",
               output=CellOutput(stdout="hello", result_repr="42")))
    md = export_markdown(d)
    assert "hello42" not in md
    assert "hello\n42" in md
