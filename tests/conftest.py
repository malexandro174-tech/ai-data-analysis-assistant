from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import Settings
from app.services.analysis_service import AnalysisService
from app.services.artifact_service import ArtifactService
from app.services.file_service import FileService
from app.services.workspace_service import WorkspaceService


@pytest.fixture()
def settings(tmp_path: Path) -> Settings:
    return Settings(storage_root=tmp_path / "storage", max_file_size=200_000, max_rows=100, max_columns=20, max_image_pixels=100_000)


@pytest.fixture()
def workspace(settings):
    service = WorkspaceService(settings); service.initialize(); return service


@pytest.fixture()
def files(settings):
    service = FileService(settings); service.initialize(); return service


@pytest.fixture()
def artifacts(settings):
    service = ArtifactService(settings); service.initialize(); return service


@pytest.fixture()
def analysis(settings): return AnalysisService(settings)
