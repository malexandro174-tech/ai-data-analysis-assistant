from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4

from app.core.config import Settings
from app.core.errors import ArtifactNotFoundError, PolicyDeniedError
from app.core.policies import inside
from app.core.schemas import ArtifactRecord


class ArtifactService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.metadata_dir / "artifacts.json"

    def initialize(self) -> None:
        self.settings.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.settings.metadata_dir.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _all(self) -> dict[str, dict]:
        self.initialize()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, values: dict[str, dict]) -> None:
        self.path.write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")

    def register(self, session_id: UUID, source_file_id: UUID | None, artifact_type: str, name: str, path: Path,
                 metadata: dict | None = None) -> ArtifactRecord:
        current = self.list_for_session(session_id)
        if len(current) >= self.settings.max_artifacts_per_session:
            raise PolicyDeniedError("Artifact limit reached")
        path = inside(self.settings.outputs_dir, path)
        record = ArtifactRecord(
            session_id=session_id, source_file_id=source_file_id, type=artifact_type, name=name[:160],
            storage_path=str(path.relative_to(self.settings.storage_root)).replace("\\", "/"),
            download_url=f"/artifacts/{uuid4()}", size_bytes=path.stat().st_size, metadata=metadata or {},
        )
        record.download_url = f"/artifacts/{record.artifact_id}"
        values = self._all()
        values[str(record.artifact_id)] = record.model_dump(mode="json")
        self._save(values)
        return record

    def get(self, artifact_id: UUID, session_id: UUID) -> ArtifactRecord:
        payload = self._all().get(str(artifact_id))
        if not payload:
            raise ArtifactNotFoundError()
        record = ArtifactRecord.model_validate(payload)
        if record.session_id != session_id:
            raise ArtifactNotFoundError()
        return record

    def path_for(self, record: ArtifactRecord) -> Path:
        return inside(self.settings.storage_root, self.settings.storage_root / record.storage_path)

    def list_for_session(self, session_id: UUID) -> list[ArtifactRecord]:
        return [ArtifactRecord.model_validate(value) for value in self._all().values() if value["session_id"] == str(session_id)]
