from pathlib import Path
import re


def test_secret_scan():
    root = Path(__file__).parents[1]
    expression = re.compile(r"(?:\d{8,12}:[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})")
    hits = []
    for path in root.rglob("*"):
        if path.is_file() and ".runtime-venv" not in path.parts and ".venv" not in path.parts and path.suffix in {".py", ".md", ".yml", ".txt"}:
            if expression.search(path.read_text(encoding="utf-8", errors="ignore")):
                hits.append(path)
    assert hits == []
