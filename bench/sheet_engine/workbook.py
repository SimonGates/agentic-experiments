from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from sheet_engine.ast import Expr
from sheet_engine.deps import collect_refs, cycle_nodes
from sheet_engine.errors import CYCLE, ERROR, ErrorValue
from sheet_engine.evaluator import Value, canon_num, eval_expr, value_kind
from sheet_engine.parser import ParseError, parse_formula

_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")


class Cell:
    __slots__ = ("raw", "formula", "literal")

    def __init__(self, raw: str, formula: Expr | None, literal: Value) -> None:
        self.raw = raw
        self.formula = formula
        self.literal = literal


class Workbook:
    def __init__(self, cells: dict[str, str] | None = None) -> None:
        self._raw: dict[str, str] = {}
        self._cells: dict[str, Cell] = {}
        self._values: dict[str, Value] = {}
        self._cycles: set[str] = set()
        if cells:
            for addr, raw in cells.items():
                self.set_cell(addr, raw, recompute=False)
            self.recompute()

    @classmethod
    def load(cls, path: str | Path) -> Workbook:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        cells = data.get("cells", {})
        raw_cells = {str(k): _coerce_raw(v) for k, v in cells.items()}
        return cls(raw_cells)

    def save_raw(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps({"cells": dict(self._raw)}, indent=2) + "\n",
            encoding="utf-8",
        )

    def set_cell(self, addr: str, raw: str, *, recompute: bool = True) -> None:
        addr = addr.strip().upper()
        self._raw[addr] = raw
        self._cells[addr] = _parse_cell(raw)
        if recompute:
            self.recompute()

    def get_cell(self, addr: str) -> dict[str, Any]:
        addr = addr.strip().upper()
        raw = self._raw.get(addr, "")
        if addr in self._values:
            value = self._values[addr]
        elif addr in self._raw:
            value = ERROR
        else:
            value = None
        return format_cell(raw, value)

    def eval_all(self) -> dict[str, Any]:
        cells = {addr: format_cell(self._raw[addr], self._values.get(addr)) for addr in self._raw}
        return {"cells": cells}

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.eval_all(), indent=indent, ensure_ascii=False)

    def recompute(self) -> None:
        graph: dict[str, set[str]] = {}
        for addr, cell in self._cells.items():
            if cell.formula is not None:
                graph[addr] = collect_refs(cell.formula)
            else:
                graph[addr] = set()
        self._cycles = cycle_nodes(graph)
        self._values = {}
        evaluating: set[str] = set()

        def lookup(addr: str) -> Value:
            return eval_one(addr)

        def eval_one(addr: str) -> Value:
            if addr in self._values:
                return self._values[addr]
            if addr in self._cycles:
                self._values[addr] = CYCLE
                return CYCLE
            if addr not in self._cells:
                return None
            if addr in evaluating:
                self._values[addr] = CYCLE
                return CYCLE
            cell = self._cells[addr]
            if cell.formula is None:
                self._values[addr] = cell.literal
                return cell.literal
            evaluating.add(addr)
            try:
                val = eval_expr(cell.formula, lookup)
            except ParseError:
                val = ERROR
            evaluating.discard(addr)
            self._values[addr] = val
            return val

        for addr in self._cells:
            eval_one(addr)


def _coerce_raw(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return str(value)


def _parse_literal(raw: str) -> Value:
    if raw == "":
        return None
    if raw == "TRUE":
        return True
    if raw == "FALSE":
        return False
    if _NUMBER_RE.match(raw):
        if "." in raw:
            return canon_num(float(raw))
        return int(raw)
    return raw


def _parse_cell(raw: str) -> Cell:
    if raw.startswith("="):
        try:
            formula = parse_formula(raw)
            return Cell(raw, formula, None)
        except ParseError:
            return Cell(raw, None, ERROR)
    return Cell(raw, None, _parse_literal(raw))


def format_cell(raw: str, value: Value) -> dict[str, Any]:
    if isinstance(value, ErrorValue):
        return {"raw": raw, "value": value.code, "type": "error"}
    kind = value_kind(value)
    if kind == "empty":
        return {"raw": raw, "value": None, "type": "empty"}
    if kind == "number" and isinstance(value, (int, float)):
        return {"raw": raw, "value": canon_num(value), "type": "number"}
    if kind == "boolean":
        return {"raw": raw, "value": bool(value), "type": "boolean"}
    return {"raw": raw, "value": value, "type": "string"}
