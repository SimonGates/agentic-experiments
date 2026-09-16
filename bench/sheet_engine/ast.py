from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Number:
    value: int | float


@dataclass(frozen=True)
class String:
    value: str


@dataclass(frozen=True)
class Boolean:
    value: bool


@dataclass(frozen=True)
class CellRef:
    col: str
    row: int

    @property
    def addr(self) -> str:
        return f"{self.col}{self.row}"

    @property
    def valid(self) -> bool:
        return len(self.col) == 1 and "A" <= self.col <= "Z" and 1 <= self.row <= 99


@dataclass(frozen=True)
class Range:
    start: CellRef
    end: CellRef


@dataclass(frozen=True)
class UnaryOp:
    op: str
    operand: Expr


@dataclass(frozen=True)
class BinaryOp:
    op: str
    left: Expr
    right: Expr


@dataclass(frozen=True)
class FunctionCall:
    name: str
    args: tuple[Expr, ...]


Expr = Number | String | Boolean | CellRef | Range | UnaryOp | BinaryOp | FunctionCall
