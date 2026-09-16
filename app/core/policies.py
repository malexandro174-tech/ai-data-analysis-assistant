from __future__ import annotations

from pathlib import Path
import re

from app.core.errors import PolicyDeniedError


ALLOWED_ACTIONS = {"preview", "analyze", "generate_chart", "generate_report", "save_summary"}
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".png", ".jpg", ".jpeg", ".webp"}
TABLE_EXTENSIONS = {".csv", ".xlsx", ".xls"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SAFE_NAME = re.compile(r"[^A-Za-zА-Яа-я0-9._ -]+")


def safe_filename(name: str) -> str:
    candidate = Path(name).name.strip().replace("\x00", "")
    candidate = SAFE_NAME.sub("_", candidate)
    if not candidate or candidate in {".", ".."}:
        raise PolicyDeniedError("Unsafe filename")
    return candidate[:160]


def ensure_action(action: str) -> None:
    if action not in ALLOWED_ACTIONS:
        raise PolicyDeniedError("Unknown action")


def inside(root: Path, candidate: Path) -> Path:
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    if resolved_root != resolved_candidate and resolved_root not in resolved_candidate.parents:
        raise PolicyDeniedError("Path traversal")
    return resolved_candidate
