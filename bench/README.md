# sheet

Mini spreadsheet CLI. Stdlib-only engine; formulas per the repo `spec.md`.

## Commands

```
./sheet eval workbook.json
./sheet get workbook.json C1
./sheet set workbook.json D1 "=A1-B1" --eval
```

## Tests

From the repo root:

```
python -m pytest bench/tests -q
```

From `bench/`:

```
python -m pytest tests -q
```
