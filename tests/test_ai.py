from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.core.errors import AIServiceRequestError
from app.core.schemas import DatasetSummary
from app.services.ai_service import AIService


class Provider:
    async def plan(self, question, context):
        return {"raw": '{"assistant_message":"Готово","actions":[{"type":"analyze"}]}', "resolved_model": "deepseek-flash"}
    async def vision(self, mime, image, question): return "Красный квадрат", "deepseek-flash"


class FailingProvider:
    async def plan(self, question, context): raise AIServiceRequestError()
    async def vision(self, mime, image, question): raise AIServiceRequestError()


@pytest.mark.asyncio
async def test_structured_provider_plan():
    service = AIService(Provider()); plan = await service.plan("Проанализируй", DatasetSummary(row_count=1, column_count=1, columns=[], preview=[]))
    assert plan.actions[0].type == "analyze" and service.resolved_model == "deepseek-flash"


@pytest.mark.asyncio
async def test_provider_failure_fallback():
    service = AIService(FailingProvider()); plan = await service.plan("Проанализируй", None)
    assert "Загрузите" in plan.assistant_message


@pytest.mark.asyncio
async def test_vision_analysis():
    path = Path(__file__)
    answer = await AIService(Provider()).vision(path, "image/png", "Что на изображении?")
    assert answer == "Красный квадрат"


@pytest.mark.asyncio
async def test_vision_provider_failure():
    with pytest.raises(AIServiceRequestError): await AIService(FailingProvider()).vision(Path(__file__), "image/png", "test")
