from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def plan(self, question: str, data_context: dict) -> dict: ...

    @abstractmethod
    async def vision(self, mime_type: str, image_bytes: bytes, question: str) -> tuple[str, str | None]: ...
