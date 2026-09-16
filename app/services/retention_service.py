from __future__ import annotations

from datetime import datetime, timedelta

from app.core.config import Settings
from app.core.schemas import RetentionResult


class RetentionService:
    def __init__(self, settings: Settings): self.settings = settings

    def cleanup(self, apply: bool = False) -> RetentionResult:
        threshold = datetime.utcnow() - timedelta(days=self.settings.retention_days)
        eligible = deleted = 0
        for root in (self.settings.uploads_dir, self.settings.outputs_dir):
            if not root.exists(): continue
            for path in root.rglob("*"):
                if path.is_file() and datetime.utcfromtimestamp(path.stat().st_mtime) < threshold:
                    eligible += 1
                    if apply:
                        path.unlink(); deleted += 1
        return RetentionResult(eligible_files=eligible, deleted_files=deleted)
