from __future__ import annotations

from sheet_engine.ast import (
    BinaryOp,
    Boolean,
    CellRef,
    Expr,
    FunctionCall,
    Number,
    Range,
    String,
    UnaryOp,
)


def col_index(col: str) -> int:
    return ord(col) - ord("A")


def index_col(idx: int) -> str:
    return chr(ord("A") + idx)


def expand_range(rng: Range) -> list[str]:
    if not rng.start.valid or not rng.end.valid:
        return []
    c1, c2 = col_index(rng.start.col), col_index(rng.end.col)
    r1, r2 = rng.start.row, rng.end.row
    if c1 > c2:
        c1, c2 = c2, c1
    if r1 > r2:
        r1, r2 = r2, r1
    addrs: list[str] = []
    for row in range(r1, r2 + 1):
        for col_i in range(c1, c2 + 1):
            addrs.append(f"{index_col(col_i)}{row}")
    return addrs


def collect_refs(expr: Expr) -> set[str]:
    refs: set[str] = set()
    _walk(expr, refs)
    return refs


def _walk(expr: Expr, refs: set[str]) -> None:
    if isinstance(expr, (Number, String, Boolean)):
        return
    if isinstance(expr, CellRef):
        if expr.valid:
            refs.add(expr.addr)
        return
    if isinstance(expr, Range):
        refs.update(expand_range(expr))
        return
    if isinstance(expr, UnaryOp):
        _walk(expr.operand, refs)
        return
    if isinstance(expr, BinaryOp):
        _walk(expr.left, refs)
        _walk(expr.right, refs)
        return
    if isinstance(expr, FunctionCall):
        for arg in expr.args:
            _walk(arg, refs)


def cycle_nodes(graph: dict[str, set[str]]) -> set[str]:
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    cycles: set[str] = set()

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        for w in graph.get(v, ()):
            if w not in graph:
                continue
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1 or v in graph.get(v, ()):
                cycles.update(scc)

    for node in graph:
        if node not in indices:
            strongconnect(node)
    return cycles
