from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CellOutput:
    stdout: str = ""
    stderr: str = ""
    result_repr: str = ""
    result_html: str | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "result_repr": self.result_repr,
            "result_html": self.result_html,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CellOutput":
        return cls(
            stdout=d.get("stdout", ""),
            stderr=d.get("stderr", ""),
            result_repr=d.get("result_repr", ""),
            result_html=d.get("result_html"),
            error=d.get("error"),
        )


CELL_TYPES = ("code", "note", "prompt", "ai")


@dataclass
class Cell:
    id: str
    type: str
    source: str = ""
    output: CellOutput | None = None
    include_in_context: bool = True
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in CELL_TYPES:
            raise ValueError(f"type must be one of {CELL_TYPES}, got {self.type!r}")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "source": self.source,
            "output": self.output.to_dict() if self.output else None,
            "include_in_context": self.include_in_context,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Cell":
        out = d.get("output")
        return cls(
            id=d["id"],
            type=d["type"],
            source=d.get("source", ""),
            output=CellOutput.from_dict(out) if out else None,
            include_in_context=d.get("include_in_context", True),
            metadata=d.get("metadata", {}),
        )


@dataclass
class Document:
    cells: list[Cell] = field(default_factory=list)

    def get(self, cell_id: str) -> Cell:
        return self.cells[self._index(cell_id)]

    def index(self, cell_id: str) -> int:
        return self._index(cell_id)

    def _index(self, cell_id: str) -> int:
        for i, c in enumerate(self.cells):
            if c.id == cell_id:
                return i
        raise KeyError(cell_id)

    def add(self, cell: Cell, index: int | None = None) -> None:
        if index is None:
            self.cells.append(cell)
        else:
            self.cells.insert(index, cell)

    def delete(self, cell_id: str) -> None:
        self.cells.pop(self._index(cell_id))

    def move(self, cell_id: str, direction: str) -> None:
        if direction not in ("up", "down"):
            raise ValueError(f"direction must be 'up' or 'down', got {direction!r}")
        i = self._index(cell_id)
        j = i - 1 if direction == "up" else i + 1
        if 0 <= j < len(self.cells):
            self.cells[i], self.cells[j] = self.cells[j], self.cells[i]

    def cells_above(self, cell_id: str) -> list[Cell]:
        return self.cells[: self._index(cell_id)]

    def to_dict(self) -> dict:
        return {"cells": [c.to_dict() for c in self.cells]}

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        return cls(cells=[Cell.from_dict(c) for c in d.get("cells", [])])
