from __future__ import annotations

import aiohttp

from app.core.config import Settings
from app.core.errors import AIServiceConfigurationError, AIServiceRequestError


class BrokerAccessAdapter:
    """Credential-free Broker adapter; the application never receives provider keys."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def _post(self, path: str, payload: dict, timeout: int = 45) -> dict:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(f"{self.settings.broker_url}{path}", json=payload) as response:
                    data = await response.json(content_type=None)
                    if response.status >= 400:
                        raise AIServiceRequestError(str(data.get("error", "Broker rejected request")))
                    return data
        except aiohttp.ClientError as exc:
            raise AIServiceConfigurationError() from exc

    async def validate(self) -> None:
        for capability in ("CHAT_COMPLETION", "TEXT_ANALYSIS", "VISION_ANALYSIS"):
            result = await self._post("/access/request", {
                "requester_id": self.settings.requester_id,
                "service_id": "deepseek",
                "capability": capability,
            })
            if result.get("result") != "GRANTED":
                raise AIServiceConfigurationError()

    async def complete(self, payload: dict, capability: str = "CHAT_COMPLETION") -> dict:
        return await self._post("/deepseek/complete", {
            "requester_id": self.settings.requester_id,
            "capability": capability,
            "payload": payload,
        })
