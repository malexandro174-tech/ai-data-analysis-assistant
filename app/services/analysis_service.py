from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

import pandas as pd

from app.core.config import Settings
from app.core.errors import AnalysisError, FileReadError
from app.core.schemas import DatasetSummary, compact_json


class AnalysisService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def read(self, path: Path, extension: str) -> pd.DataFrame:
        try:
            if extension == ".csv":
                frame = pd.read_csv(path, nrows=self.settings.max_rows + 1)
            elif extension in {".xlsx", ".xls"}:
                frame = pd.read_excel(path, nrows=self.settings.max_rows + 1)
            elif extension == ".json":
                raw = json.loads(path.read_text(encoding="utf-8-sig"))
                frame = pd.json_normalize(raw) if isinstance(raw, (list, dict)) else pd.DataFrame({"value": raw})
            else:
                raise AnalysisError("Not a dataset")
        except (ValueError, UnicodeDecodeError, OSError, json.JSONDecodeError) as exc:
            raise FileReadError() from exc
        if frame.empty:
            raise AnalysisError("Dataset is empty")
        if len(frame) > self.settings.max_rows or len(frame.columns) > self.settings.max_columns:
            raise AnalysisError("Dataset exceeds row or column limit")
        frame.columns = [str(column)[:120] for column in frame.columns]
        return frame

    @staticmethod
    def classify(series: pd.Series) -> str:
        if pd.api.types.is_bool_dtype(series):
            return "boolean"
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        non_null = series.dropna()
        if non_null.empty:
            return "unknown"
        parsed_dates = pd.to_datetime(non_null, errors="coerce")
        if parsed_dates.notna().mean() >= 0.85 and len(non_null) > 1:
            return "datetime"
        unique = non_null.nunique()
        if unique <= min(40, max(8, len(non_null) * 0.35)):
            return "categorical"
        return "text"

    def summarize(self, frame: pd.DataFrame) -> DatasetSummary:
        columns: list[dict] = []
        date_ranges: dict[str, dict] = {}
        for name in frame.columns:
            series = frame[name]
            classification = self.classify(series)
            entry = {"name": name, "dtype": str(series.dtype), "classification": classification,
                     "missing": int(series.isna().sum()), "unique": int(series.nunique(dropna=True))}
            if classification == "numeric":
                entry["statistics"] = {key: compact_json(value) for key, value in {
                    "min": series.min(), "max": series.max(), "mean": series.mean(), "median": series.median(),
                }.items()}
            if classification == "datetime":
                parsed = pd.to_datetime(series, errors="coerce")
                date_ranges[name] = {"min": str(parsed.min()) if parsed.notna().any() else None,
                                     "max": str(parsed.max()) if parsed.notna().any() else None}
            columns.append(entry)
        preview = [{key: compact_json(value) for key, value in row.items()} for row in frame.head(8).to_dict("records")]
        return DatasetSummary(row_count=len(frame), column_count=len(frame.columns), columns=columns, preview=preview, date_ranges=date_ranges)

    def concise_findings(self, summary: DatasetSummary) -> str:
        numeric = [column["name"] for column in summary.columns if column["classification"] == "numeric"]
        missing = [f"{column['name']}: {column['missing']}" for column in summary.columns if column["missing"]]
        result = f"Файл содержит {summary.row_count} строк и {summary.column_count} столбцов."
        if numeric:
            result += f" Числовые поля: {', '.join(numeric[:6])}."
        if missing:
            result += f" Пропуски: {', '.join(missing[:4])}."
        return result
