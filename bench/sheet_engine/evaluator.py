from __future__ import annotations

from collections.abc import Callable

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
from sheet_engine.deps import expand_range
from sheet_engine.errors import DIVZERO, ERROR, ErrorValue

Value = int | float | str | bool | None | ErrorValue

Lookup = Callable[[str], Value]


def canon_num(n: int | float) -> int | float:
    if isinstance(n, bool):
        return int(n)
    if isinstance(n, float):
        if n == 0:
            return 0
        if n.is_integer() and abs(n) <= 2**53:
            return int(n)
    return n


def value_kind(v: Value) -> str:
    if isinstance(v, ErrorValue):
        return "error"
    if v is None:
        return "empty"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "number"
    return "string"


def to_str(v: Value) -> str | ErrorValue:
    if isinstance(v, ErrorValue):
        return v
    if v is None:
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    if isinstance(v, (int, float)):
        n = canon_num(v)
        return str(n)
    return v


def to_num(v: Value) -> int | float | ErrorValue:
    if isinstance(v, ErrorValue):
        return v
    if v is None:
        return 0
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    return ERROR


def is_truthy(v: Value) -> bool | ErrorValue:
    if isinstance(v, ErrorValue):
        return v
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return ERROR


def eval_expr(expr: Expr, lookup: Lookup) -> Value:
    return _eval(expr, lookup)


def _eval(expr: Expr, lookup: Lookup) -> Value:
    if isinstance(expr, Number):
        return canon_num(expr.value)
    if isinstance(expr, String):
        return expr.value
    if isinstance(expr, Boolean):
        return expr.value
    if isinstance(expr, CellRef):
        if not expr.valid:
            return ERROR
        return lookup(expr.addr)
    if isinstance(expr, Range):
        return ERROR
    if isinstance(expr, UnaryOp):
        if expr.op == "-":
            val = _eval(expr.operand, lookup)
            n = to_num(val)
            if isinstance(n, ErrorValue):
                return n
            return canon_num(-n)
        return ERROR
    if isinstance(expr, BinaryOp):
        return _eval_binary(expr, lookup)
    if isinstance(expr, FunctionCall):
        return _eval_func(expr, lookup)
    return ERROR


def _eval_binary(expr: BinaryOp, lookup: Lookup) -> Value:
    if expr.op == "&":
        left = _eval(expr.left, lookup)
        right = _eval(expr.right, lookup)
        a = to_str(left)
        b = to_str(right)
        if isinstance(a, ErrorValue):
            return a
        if isinstance(b, ErrorValue):
            return b
        return a + b
    if expr.op in {"+", "-", "*", "/"}:
        left = _eval(expr.left, lookup)
        right = _eval(expr.right, lookup)
        a = to_num(left)
        b = to_num(right)
        if isinstance(a, ErrorValue):
            return a
        if isinstance(b, ErrorValue):
            return b
        if expr.op == "+":
            return canon_num(a + b)
        if expr.op == "-":
            return canon_num(a - b)
        if expr.op == "*":
            return canon_num(a * b)
        if b == 0:
            return DIVZERO
        return canon_num(a / b)
    if expr.op in {"=", "<>", ">", ">=", "<", "<="}:
        left = _eval(expr.left, lookup)
        right = _eval(expr.right, lookup)
        return _compare(expr.op, left, right)
    return ERROR


def _compare(op: str, left: Value, right: Value) -> Value:
    if isinstance(left, ErrorValue):
        return left
    if isinstance(right, ErrorValue):
        return right
    lk, rk = value_kind(left), value_kind(right)
    if lk == "empty" and rk == "empty":
        l: Value = None
        r: Value = None
    elif lk == "empty" and rk == "number":
        l, r = 0, right
        lk = "number"
    elif rk == "empty" and lk == "number":
        l, r = left, 0
        rk = "number"
    elif lk == "empty" and rk == "string":
        l, r = "", right
        lk = "string"
    elif rk == "empty" and lk == "string":
        l, r = left, ""
        rk = "string"
    elif lk == "empty" and rk == "boolean":
        l, r = False, right
        lk = "boolean"
    elif rk == "empty" and lk == "boolean":
        l, r = left, False
        rk = "boolean"
    else:
        l, r = left, right
    if lk != rk:
        return ERROR
    if op == "=":
        return l == r
    if op == "<>":
        return l != r
    if lk not in {"number", "string"}:
        return ERROR
    assert l is not None and r is not None
    if op == ">":
        return l > r
    if op == ">=":
        return l >= r
    if op == "<":
        return l < r
    if op == "<=":
        return l <= r
    return ERROR


def _flatten_arg(arg: Expr, lookup: Lookup) -> list[Value] | ErrorValue:
    if isinstance(arg, Range):
        if not arg.start.valid or not arg.end.valid:
            return ERROR
        return [lookup(addr) for addr in expand_range(arg)]
    val = _eval(arg, lookup)
    if isinstance(val, ErrorValue):
        return val
    return [val]


def _flatten_args(args: tuple[Expr, ...], lookup: Lookup) -> list[Value] | ErrorValue:
    out: list[Value] = []
    for arg in args:
        part = _flatten_arg(arg, lookup)
        if isinstance(part, ErrorValue):
            return part
        for v in part:
            if isinstance(v, ErrorValue):
                return v
            out.append(v)
    return out


def _collect_numerics(args: tuple[Expr, ...], lookup: Lookup) -> list[int | float] | ErrorValue:
    nums: list[int | float] = []
    for arg in args:
        if isinstance(arg, Range):
            if not arg.start.valid or not arg.end.valid:
                return ERROR
            for addr in expand_range(arg):
                v = lookup(addr)
                if isinstance(v, ErrorValue):
                    return v
                if v is None or isinstance(v, str):
                    continue
                if isinstance(v, bool):
                    nums.append(1 if v else 0)
                elif isinstance(v, (int, float)):
                    nums.append(v)
                else:
                    return ERROR
            continue
        v = _eval(arg, lookup)
        if isinstance(v, ErrorValue):
            return v
        if v is None:
            continue
        if isinstance(v, bool):
            nums.append(1 if v else 0)
        elif isinstance(v, (int, float)):
            nums.append(v)
        else:
            return ERROR
    return nums


def _eval_func(call: FunctionCall, lookup: Lookup) -> Value:
    name = call.name
    if name == "IF":
        if len(call.args) != 3:
            return ERROR
        cond = is_truthy(_eval(call.args[0], lookup))
        if isinstance(cond, ErrorValue):
            return cond
        return _eval(call.args[1] if cond else call.args[2], lookup)
    if name == "NOT":
        if len(call.args) != 1:
            return ERROR
        t = is_truthy(_eval(call.args[0], lookup))
        if isinstance(t, ErrorValue):
            return t
        return not t
    if name == "LEN":
        if len(call.args) != 1:
            return ERROR
        s = to_str(_eval(call.args[0], lookup))
        if isinstance(s, ErrorValue):
            return s
        return len(s)
    if name == "SUM":
        nums = _collect_numerics(call.args, lookup)
        if isinstance(nums, ErrorValue):
            return nums
        return canon_num(sum(nums))
    if name == "AVG":
        nums = _collect_numerics(call.args, lookup)
        if isinstance(nums, ErrorValue):
            return nums
        if not nums:
            return DIVZERO
        return canon_num(sum(nums) / len(nums))
    if name == "MIN":
        nums = _collect_numerics(call.args, lookup)
        if isinstance(nums, ErrorValue):
            return nums
        if not nums:
            return ERROR
        return canon_num(min(nums))
    if name == "MAX":
        nums = _collect_numerics(call.args, lookup)
        if isinstance(nums, ErrorValue):
            return nums
        if not nums:
            return ERROR
        return canon_num(max(nums))
    if name == "CONCAT":
        flat = _flatten_args(call.args, lookup)
        if isinstance(flat, ErrorValue):
            return flat
        parts: list[str] = []
        for v in flat:
            s = to_str(v)
            if isinstance(s, ErrorValue):
                return s
            parts.append(s)
        return "".join(parts)
    if name == "AND":
        if not call.args:
            return True
        flat = _flatten_args(call.args, lookup)
        if isinstance(flat, ErrorValue):
            return flat
        for v in flat:
            t = is_truthy(v)
            if isinstance(t, ErrorValue):
                return t
            if not t:
                return False
        return True
    if name == "OR":
        if not call.args:
            return False
        flat = _flatten_args(call.args, lookup)
        if isinstance(flat, ErrorValue):
            return flat
        for v in flat:
            t = is_truthy(v)
            if isinstance(t, ErrorValue):
                return t
            if t:
                return True
        return False
    return ERROR
