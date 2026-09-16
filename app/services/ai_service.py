from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.errors import AIServiceRequestError, PolicyDeniedError
from app.core.policies import ensure_action
from app.core.schemas import AIPlan, Action, DatasetSummary
from app.providers.llm_base import LLMProvider

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self, provider: LLMProvider): self.provider = provider; self.resolved_model: str | None = None

    @staticmethod
    def context(summary: DatasetSummary | None) -> dict:
        if not summary: return {"file_available": False}
        return {"file_available": True, "rows": summary.row_count, "columns": summary.column_count,
                "schema": [{key: value for key, value in column.items() if key in {"name", "classification", "missing", "unique"}} for column in summary.columns],
                "preview": summary.preview[:4]}

    @staticmethod
    def fallback(question: str, summary: DatasetSummary | None) -> AIPlan:
        text = question.lower()
        actions: list[Action] = []
        if any(word in text for word in ("preview", "покажи")): actions.append(Action(type="preview"))
        if any(word in text for word in ("анализ", "проанализ", "метрик", "кратко")): actions.append(Action(type="analyze"))
        if any(word in text for word in ("граф", "chart", "line", "bar", "scatter", "pie", "hist")):
            chart = next((kind for kind in ("scatter", "pie", "histogram", "bar", "line") if kind in text), "bar")
            actions.append(Action(type="generate_chart", chart_type=chart))
        if "отчёт" in text or "report" in text: actions.append(Action(type="generate_report"))
        if "summary" in text or "сохрани" in text or "markdown" in text: actions.append(Action(type="save_summary"))
        if not actions and summary: actions = [Action(type="analyze")]
        if not summary:
            message = "Загрузите CSV, Excel или JSON для анализа. Изображение можно отправить для multimodal-анализа."
        else:
            message = f"Готово. Доступны {summary.row_count} строк и {summary.column_count} столбцов; все вычисления выполняются локальными инструментами."
        return AIPlan(assistant_message=message, actions=actions)

    async def plan(self, question: str, summary: DatasetSummary | None) -> AIPlan:
        fallback = self.fallback(question, summary)
        try:
            response = await self.provider.plan(question, self.context(summary))
            self.resolved_model = response.get("resolved_model")
            raw = response["raw"].strip()
            if raw.startswith("```"):
                raw = raw.strip("`").removeprefix("json").strip()
            plan = AIPlan.model_validate_json(raw)
            for action in plan.actions: ensure_action(action.type)
            return plan
        except (AIServiceRequestError, ValueError, json.JSONDecodeError, PolicyDeniedError) as exc:
            logger.info("provider_plan_fallback", extra={"reason": type(exc).__name__})
            return fallback

    async def vision(self, path: Path, mime_type: str, question: str) -> str:
        try:
            answer, model = await self.provider.vision(mime_type, path.read_bytes(), question)
            self.resolved_model = model
            return answer
        except (OSError, AIServiceRequestError) as exc:
            logger.warning("vision_unavailable", extra={"reason": type(exc).__name__})
            raise AIServiceRequestError() from exc
