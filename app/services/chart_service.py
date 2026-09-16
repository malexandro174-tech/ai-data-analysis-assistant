from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from app.core.errors import ChartGenerationError
from app.core.policies import inside


class ChartService:
    SUPPORTED = {"line", "bar", "histogram", "scatter", "pie"}

    def generate(self, frame: pd.DataFrame, output_root: Path, session_id: UUID, chart_type: str,
                 x_column: str | None = None, y_column: str | None = None) -> Path:
        if chart_type not in self.SUPPORTED:
            raise ChartGenerationError()
        numeric = list(frame.select_dtypes(include="number").columns)
        x_column = x_column if x_column in frame.columns else (frame.columns[0] if len(frame.columns) else None)
        y_column = y_column if y_column in numeric else (numeric[0] if numeric else None)
        if chart_type in {"line", "bar", "scatter", "pie"} and not y_column:
            raise ChartGenerationError()
        if chart_type == "scatter" and (not x_column or x_column not in numeric):
            x_column = numeric[0] if numeric else None
            if not x_column:
                raise ChartGenerationError()
        session_dir = inside(output_root, output_root / str(session_id))
        session_dir.mkdir(parents=True, exist_ok=True)
        target = inside(session_dir, session_dir / f"chart-{uuid4()}.png")
        figure, axis = plt.subplots(figsize=(8, 4.8), dpi=130)
        try:
            if chart_type == "histogram":
                series = frame[y_column].dropna()
                if series.empty:
                    raise ChartGenerationError()
                axis.hist(series, bins=min(20, max(5, int(series.nunique()))), color="#8b5cf6", edgecolor="#1f1638")
                axis.set_xlabel(str(y_column)); axis.set_ylabel("Частота"); axis.set_title(f"Распределение: {y_column}")
            elif chart_type == "scatter":
                axis.scatter(frame[x_column], frame[y_column], color="#16b8a6", alpha=0.8)
                axis.set_xlabel(str(x_column)); axis.set_ylabel(str(y_column)); axis.set_title(f"Связь: {x_column} и {y_column}")
            elif chart_type == "pie":
                series = frame.groupby(x_column, dropna=True)[y_column].sum().sort_values(ascending=False).head(8)
                if series.empty:
                    raise ChartGenerationError()
                axis.pie(series.values, labels=[str(index) for index in series.index], autopct="%1.0f%%")
                axis.set_title(f"Структура: {y_column} по {x_column}")
            else:
                data = frame[[x_column, y_column]].dropna().head(500)
                if data.empty:
                    raise ChartGenerationError()
                if chart_type == "line":
                    axis.plot(data[x_column], data[y_column], color="#16b8a6", marker="o", markersize=3, label=str(y_column))
                else:
                    grouped = data.groupby(x_column, dropna=True)[y_column].sum().head(24)
                    axis.bar([str(index) for index in grouped.index], grouped.values, color="#8b5cf6", label=str(y_column))
                    axis.tick_params(axis="x", rotation=35)
                axis.set_xlabel(str(x_column)); axis.set_ylabel(str(y_column)); axis.set_title(f"{chart_type.title()}: {y_column}"); axis.legend()
            figure.tight_layout()
            figure.savefig(target, format="png")
        except (ValueError, TypeError) as exc:
            raise ChartGenerationError() from exc
        finally:
            plt.close(figure)
        return target
