from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


ActionType = Literal["preview", "analyze", "generate_chart", "generate_report", "save_summary"]
ArtifactType = Literal["chart_png", "report_docx", "summary_md"]


class Action(BaseModel):
    type: ActionType
    chart_type: Literal["line", "bar", "histogram", "scatter", "pie"] | None = None
    x_column: str | None = Field(default=None, max_length=120)
    y_column: str | None = Field(default=None, max_length=120)


class AIPlan(BaseModel):
    assistant_message: str = Field(min_length=1, max_length=2500)
    actions: list[Action] = Field(default_factory=list, max_length=5)


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(max_length=2500)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseModel):
    conversation_id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    messages: list[Message] = Field(default_factory=list)
    active_file_id: UUID | None = None
    artifact_ids: list[UUID] = Field(default_factory=list)


class FileRecord(BaseModel):
    file_id: UUID = Field(default_factory=uuid4)
    original_name: str
    saved_name: str
    extension: str
    content_type: str
    size_bytes: int
    kind: Literal["table", "json", "image"]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    session_id: UUID
    relative_path: str
    storage_url: str
    status: Literal["stored", "rejected"] = "stored"


class ArtifactRecord(BaseModel):
    artifact_id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    source_file_id: UUID | None = None
    type: ArtifactType
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    storage_path: str
    download_url: str
    size_bytes: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetSummary(BaseModel):
    row_count: int
    column_count: int
    columns: list[dict[str, Any]]
    preview: list[dict[str, Any]]
    date_ranges: dict[str, dict[str, str | None]] = Field(default_factory=dict)


class Metrics(BaseModel):
    conversations: int = 0
    uploads: int = 0
    uploads_rejected: int = 0
    analysis_requests: int = 0
    vision_requests: int = 0
    charts_generated: int = 0
    reports_generated: int = 0
    summaries_saved: int = 0
    provider_errors: int = 0
    file_errors: int = 0


class BrokerResponse(BaseModel):
    model: str | None = None
    choices: list[dict[str, Any]] = Field(default_factory=list)


class RetentionResult(BaseModel):
    eligible_files: int
    deleted_files: int


def compact_json(value: Any) -> Any:
    if isinstance(value, (datetime, UUID)):
        return str(value)
    if hasattr(value, "item"):
        return value.item()
    if value != value:  # NaN
        return None
    return value
