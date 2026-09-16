from __future__ import annotations

from pathlib import Path
import pytest

from app.core.errors import ArtifactNotFoundError


def test_session_persistence(workspace):
    created = workspace.create(); workspace.append_message(created, "user", "Привет")
    assert workspace.get(created.conversation_id).messages[0].content == "Привет"


def test_session_isolation(artifacts, workspace, settings):
    first, second = workspace.create(), workspace.create()
    path = settings.outputs_dir / str(first.conversation_id) / "test.md"; path.parent.mkdir(parents=True); path.write_text("x", encoding="utf-8")
    artifact = artifacts.register(first.conversation_id, None, "summary_md", "test.md", path)
    with pytest.raises(ArtifactNotFoundError): artifacts.get(artifact.artifact_id, second.conversation_id)


def test_artifact_download_record(artifacts, workspace, settings):
    session = workspace.create(); path = settings.outputs_dir / str(session.conversation_id) / "test.md"; path.parent.mkdir(parents=True); path.write_text("# OK", encoding="utf-8")
    artifact = artifacts.register(session.conversation_id, None, "summary_md", "test.md", path)
    assert artifacts.path_for(artifact).read_text(encoding="utf-8") == "# OK"
