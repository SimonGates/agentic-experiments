from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from sheet_engine.workbook import Workbook

BENCH = Path(__file__).resolve().parents[1]
SHEET = BENCH / "sheet"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
SAMPLE = FIXTURES / "sample.json"
INTRO = FIXTURES / "intro.json"


def cells(raw: dict[str, str]) -> dict:
    return Workbook(raw).eval_all()["cells"]


def test_sample_b2_is_big():
    out = cells(
        {
            "A1": "10",
            "A2": "20",
            "B1": "=A1+A2",
            "B2": '=IF(B1>25,"big","small")',
        }
    )
    assert out["B2"] == {
        "raw": '=IF(B1>25,"big","small")',
        "value": "big",
        "type": "string",
    }
    assert out["B1"]["value"] == 30
    assert out["B1"]["type"] == "number"


def test_arithmetic():
    out = cells({"A1": "2", "B1": "3", "C1": "=A1+B1", "A2": "=C1*2", "D1": "=A2-1", "E1": "=D1/2"})
    assert out["C1"]["value"] == 5
    assert out["A2"]["value"] == 10
    assert out["D1"]["value"] == 9
    assert out["E1"]["value"] == 4.5
    assert out["E1"]["type"] == "number"


def test_concat():
    out = cells(
        {
            "A1": "2",
            "B1": "3",
            "C1": "=A1+B1",
            "A2": "=C1*2",
            "B2": "hello",
            "C2": '=A2&" "&B2',
        }
    )
    assert out["C2"] == {"raw": '=A2&" "&B2', "value": "10 hello", "type": "string"}


def test_if():
    out = cells({"A1": "1", "B1": '=IF(A1=1,"yes","no")', "C1": '=IF(A1>1,"yes","no")'})
    assert out["B1"]["value"] == "yes"
    assert out["C1"]["value"] == "no"


def test_ranges_sum():
    out = cells(
        {
            "A1": "1",
            "B1": "2",
            "A2": "3",
            "B2": "4",
            "C1": "=SUM(A1:B2)",
            "C2": "=SUM(A1,B2,10)",
        }
    )
    assert out["C1"]["value"] == 10
    assert out["C2"]["value"] == 15
    assert out["C1"]["type"] == "number"


def test_divzero():
    out = cells({"A1": "=1/0", "B1": "=A1+1"})
    assert out["A1"] == {"raw": "=1/0", "value": "#DIV/0!", "type": "error"}
    assert out["B1"]["type"] == "error"
    assert out["B1"]["value"] == "#DIV/0!"


def test_cycle():
    out = cells({"A1": "=B1", "B1": "=A1"})
    assert out["A1"]["type"] == "error"
    assert out["A1"]["value"] == "#CYCLE!"
    assert out["B1"]["value"] == "#CYCLE!"
    self_ref = cells({"A1": "=A1+1"})
    assert self_ref["A1"]["value"] == "#CYCLE!"


def test_bad_ref():
    out = cells({"A1": "=A100", "B1": "=ZZ1", "C1": "=A0"})
    assert out["A1"]["value"] == "#ERROR!"
    assert out["A1"]["type"] == "error"
    assert out["B1"]["value"] == "#ERROR!"
    assert out["C1"]["value"] == "#ERROR!"


def test_quoted_number_is_string():
    out = cells({"A1": '="123"', "B1": "=A1+1", "C1": "123"})
    assert out["A1"] == {"raw": '="123"', "value": "123", "type": "string"}
    assert out["B1"]["value"] == "#ERROR!"
    assert out["B1"]["type"] == "error"
    assert out["C1"] == {"raw": "123", "value": 123, "type": "number"}


def test_true_false():
    out = cells(
        {
            "A1": "TRUE",
            "B1": "FALSE",
            "C1": "=TRUE",
            "D1": "=NOT(A1)",
            "E1": "=AND(A1,TRUE)",
            "F1": "=OR(B1,FALSE)",
        }
    )
    assert out["A1"] == {"raw": "TRUE", "value": True, "type": "boolean"}
    assert out["B1"] == {"raw": "FALSE", "value": False, "type": "boolean"}
    assert out["C1"]["value"] is True
    assert out["C1"]["type"] == "boolean"
    assert out["D1"]["value"] is False
    assert out["E1"]["value"] is True
    assert out["F1"]["value"] is False


def _run_sheet(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SHEET), *args],
        capture_output=True,
        text=True,
        check=check,
    )


def test_cli_eval_sample():
    proc = _run_sheet("eval", str(SAMPLE))
    data = json.loads(proc.stdout)
    assert data["cells"]["B2"]["value"] == "big"
    assert data["cells"]["B2"]["type"] == "string"
    assert data["cells"]["B1"]["value"] == 30


def test_cli_get_sample_b2():
    proc = _run_sheet("get", str(SAMPLE), "B2")
    data = json.loads(proc.stdout)
    assert data == {
        "raw": '=IF(B1>25,"big","small")',
        "value": "big",
        "type": "string",
    }


def test_cli_set_eval(tmp_path: Path):
    book = tmp_path / "book.json"
    book.write_text(SAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    proc = _run_sheet("set", str(book), "C1", "=A1-A2", "--eval")
    data = json.loads(proc.stdout)
    assert data["cells"]["C1"]["raw"] == "=A1-A2"
    assert data["cells"]["C1"]["value"] == -10
    assert data["cells"]["C1"]["type"] == "number"
    saved = json.loads(book.read_text(encoding="utf-8"))
    assert saved["cells"]["C1"] == "=A1-A2"


def test_cli_eval_intro_concat():
    proc = _run_sheet("eval", str(INTRO))
    data = json.loads(proc.stdout)
    assert data["cells"]["C1"]["value"] == 5
    assert data["cells"]["A2"]["value"] == 10
    assert data["cells"]["C2"]["value"] == "10 hello"
