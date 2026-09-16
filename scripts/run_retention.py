"""Safe retention job. Dry-run is the default; --apply removes only expired files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.services.retention_service import RetentionService


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Remove files older than RETENTION_DAYS")
    args = parser.parse_args()
    result = RetentionService(settings).cleanup(apply=args.apply)
    print(result.model_dump_json())
