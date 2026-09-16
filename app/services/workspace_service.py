from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.schemas import Conversation, Message, Metrics


class WorkspaceService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.metadata_dir / "workspaces.json"
        self.metrics_path = settings.metadata_dir / "metrics.json"

    def initialize(self) -> None:
        self.settings.metadata_dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")
        if not self.metrics_path.exists():
            self.metrics_path.write_text(Metrics().model_dump_json(), encoding="utf-8")

    def _all(self) -> dict[str, dict]:
        self.initialize()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, items: dict[str, dict]) -> None:
        self.path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def create(self) -> Conversation:
        conversation = Conversation()
        items = self._all()
        items[str(conversation.conversation_id)] = conversation.model_dump(mode="json")
        self._save(items)
        self.increment("conversations")
        return conversation

    def get(self, conversation_id: UUID) -> Conversation:
        payload = self._all().get(str(conversation_id))
        if not payload:
            return self.create()
        return Conversation.model_validate(payload)

    def update(self, conversation: Conversation) -> Conversation:
        conversation.updated_at = datetime.utcnow()
        if len(conversation.messages) > self.settings.history_limit:
            conversation.messages = conversation.messages[-self.settings.history_limit:]
        items = self._all()
        items[str(conversation.conversation_id)] = conversation.model_dump(mode="json")
        self._save(items)
        return conversation

    def append_message(self, conversation: Conversation, role: str, content: str) -> Conversation:
        conversation.messages.append(Message(role=role, content=content[:2500]))
        return self.update(conversation)

    def metrics(self) -> Metrics:
        self.initialize()
        return Metrics.model_validate_json(self.metrics_path.read_text(encoding="utf-8"))

    def increment(self, field: str) -> None:
        metric = self.metrics()
        setattr(metric, field, getattr(metric, field) + 1)
        self.metrics_path.write_text(metric.model_dump_json(), encoding="utf-8")
