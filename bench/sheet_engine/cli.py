from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sheet_engine.parser import parse_cell_addr
from sheet_engine.workbook import Workbook


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sheet", description="Mini spreadsheet engine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_eval = sub.add_parser("eval", help="evaluate whole workbook")
    p_eval.add_argument("workbook")

    p_get = sub.add_parser("get", help="get one computed cell")
    p_get.add_argument("workbook")
    p_get.add_argument("cell")

    p_set = sub.add_parser("set", help="set a cell")
    p_set.add_argument("workbook")
    p_set.add_argument("cell")
    p_set.add_argument("value")
    p_set.add_argument("--eval", dest="do_eval", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "eval":
        return cmd_eval(args.workbook)
    if args.cmd == "get":
        return cmd_get(args.workbook, args.cell)
    if args.cmd == "set":
        return cmd_set(args.workbook, args.cell, args.value, args.do_eval)
    return 1


def cmd_eval(path: str) -> int:
    wb = Workbook.load(path)
    print(wb.to_json(indent=2))
    return 0


def cmd_get(path: str, cell: str) -> int:
    if parse_cell_addr(cell) is None:
        print(json.dumps({"raw": "", "value": "#ERROR!", "type": "error"}))
        return 0
    wb = Workbook.load(path)
    print(json.dumps(wb.get_cell(cell), ensure_ascii=False))
    return 0


def cmd_set(path: str, cell: str, value: str, do_eval: bool) -> int:
    if parse_cell_addr(cell) is None:
        print("invalid cell address", file=sys.stderr)
        return 1
    src = Path(path)
    data = json.loads(src.read_text(encoding="utf-8"))
    cells = data.setdefault("cells", {})
    cells[cell.strip().upper()] = value
    src.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if do_eval:
        wb = Workbook.load(path)
        print(wb.to_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
