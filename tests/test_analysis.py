from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from app.core.errors import AnalysisError, FileReadError


def write_csv(path: Path): path.write_text("date,region,revenue,active\n2026-01-01,North,12,True\n2026-01-02,South,20,False\n", encoding="utf-8")


def test_dataframe_analysis(analysis, tmp_path):
    path = tmp_path / "data.csv"; write_csv(path)
    summary = analysis.summarize(analysis.read(path, ".csv"))
    assert (summary.row_count, summary.column_count) == (2, 4)
    assert summary.columns[2]["statistics"]["mean"] == 16


def test_column_classification(analysis, tmp_path):
    path = tmp_path / "data.csv"; write_csv(path); summary = analysis.summarize(analysis.read(path, ".csv"))
    kinds = {item["name"]: item["classification"] for item in summary.columns}
    assert kinds["revenue"] == "numeric" and kinds["date"] == "datetime" and kinds["active"] == "boolean"


def test_json_analysis(analysis, tmp_path):
    path = tmp_path / "data.json"; path.write_text(json.dumps([{"name": "A", "value": 4}]), encoding="utf-8")
    assert analysis.read(path, ".json").iloc[0]["value"] == 4


def test_excel_analysis(analysis, tmp_path):
    path = tmp_path / "data.xlsx"; pd.DataFrame({"value": [1, 2]}).to_excel(path, index=False)
    assert analysis.read(path, ".xlsx").shape == (2, 1)


def test_malformed_csv_rejected(analysis, tmp_path):
    path = tmp_path / "bad.csv"; path.write_bytes(b"\xff\xfe\x00")
    with pytest.raises(FileReadError): analysis.read(path, ".csv")


def test_row_limit(analysis, settings, tmp_path):
    path = tmp_path / "rows.csv"; path.write_text("x\n" + "\n".join(str(x) for x in range(101)), encoding="utf-8")
    with pytest.raises(AnalysisError): analysis.read(path, ".csv")
