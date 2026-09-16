from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def _int(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Data Analyst Workspace")
    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = _int("APP_PORT", 8000)
    storage_root: Path = Path(os.getenv("STORAGE_DIR", "/app/storage"))
    max_file_size: int = _int("MAX_FILE_SIZE", 5 * 1024 * 1024)
    max_rows: int = _int("MAX_ROWS", 50_000)
    max_columns: int = _int("MAX_COLUMNS", 150)
    max_image_pixels: int = _int("MAX_IMAGE_PIXELS", 16_000_000)
    max_artifacts_per_session: int = _int("MAX_ARTIFACTS_PER_SESSION", 30)
    history_limit: int = _int("HISTORY_LIMIT", 30)
    retention_days: int = _int("RETENTION_DAYS", 14)
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    broker_url: str = os.getenv("ANALYST_BROKER_URL", "http://credential-access-broker:8101")
    requester_id: str = os.getenv("ANALYST_REQUESTER_ID", "ai_data_analysis_workspace")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @property
    def uploads_dir(self) -> Path:
        return self.storage_root / "uploads"

    @property
    def outputs_dir(self) -> Path:
        return self.storage_root / "outputs"

    @property
    def metadata_dir(self) -> Path:
        return self.storage_root / "metadata"


settings = Settings()
