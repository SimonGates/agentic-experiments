# Task: Mini spreadsheet engine (`sheet`)

Build a CLI `sheet` that loads a workbook, evaluates formulas, and writes a fully computed grid.

Implement under `bench/`.

## Input

A JSON workbook:

```json
{
  "cells": {
    "A1": "2",
    "B1": "3",
    "C1": "=A1+B1",
    "A2": "=C1*2",
    "B2": "hello",
    "C2": "=A2&\" \"&B2"
  }
}
```

## Commands

```
sheet eval workbook.json
sheet get workbook.json C1
sheet set workbook.json D1 "=A1-B1" --eval
```

- `eval` prints the whole computed workbook as JSON.
- `get` prints one computed cell.
- `set` updates a cell and, with `--eval`, prints the recomputed book.

## Language

Support exactly these cell values and formulas:

1. Numbers (ints and decimals), strings, booleans `TRUE`/`FALSE`, and empty cells.
2. Formulas start with `=`.
3. Cell refs: `A1`, `B12` (columns A–Z only, rows 1–99).
4. Ranges: `A1:B3`.
5. Operators: `+ - * / &` (concat), comparisons `= <> > >= < <=`, unary `-`.
6. Parens and normal precedence (`*` `/` before `+` `-`; `&` after arithmetic; comparisons lowest).
7. Functions (case-insensitive):
   - `SUM(range_or_args...)`
   - `AVG(...)` (numeric cells only; ignore blanks)
   - `MIN(...)` `MAX(...)`
   - `IF(cond, then, else)`
   - `CONCAT(...)`
   - `LEN(x)`
   - `AND(...)` `OR(...)` `NOT(x)`
8. Ranges used as function args flatten in row-major order.
9. Numbers in quotes are strings, not numbers.
10. Division by zero → `#DIV/0!`
11. Bad ref / parse / type error → `#ERROR!`
12. Cycle → every cell on the cycle is `#CYCLE!` (not a crash, not a partial guess).
13. Recalc must be dependency-driven: changing `A1` updates downstream cells; unrelated cells keep prior values if you implement incremental eval (full recalc is acceptable if results match).
14. Output JSON shape:

```json
{
  "cells": {
    "A1": {"raw": "2", "value": 2, "type": "number"},
    "C1": {"raw": "=A1+B1", "value": 5, "type": "number"}
  }
}
```

Types: `number` | `string` | `boolean` | `empty` | `error`.
Error cells: `{"raw":"=A1/0","value":"#DIV/0!","type":"error"}`.

15. Evaluation is deterministic. Do not call Excel, Google Sheets, pandas, or a spreadsheet library.
16. Ship tests. At minimum cover the cases implied by the language rules above and the sample below.

## Sample

Input:

```json
{"cells":{"A1":"10","A2":"20","B1":"=A1+A2","B2":"=IF(B1>25,\"big\",\"small\")"}}
```

`sheet get book.json B2` prints:

```json
{"raw":"=IF(B1>25,\"big\",\"small\")","value":"big","type":"string"}
```
