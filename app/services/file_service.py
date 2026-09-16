from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID, uuid4
import zipfile

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.config import Settings
from app.core.errors import EmptyFileError, FileReadError, FileTooLargeError, InvalidMimeError, UnsupportedFileError
from app.core.policies import ALLOWED_EXTENSIONS, IMAGE_EXTENSIONS, TABLE_EXTENSIONS, inside, safe_filename
from app.core.schemas import FileRecord


class FileService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.path = settings.metadata_dir / "files.json"

    def initialize(self) -> None:
        for directory in (self.settings.uploads_dir, self.settings.outputs_dir, self.settings.metadata_dir):
            directory.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("{}", encoding="utf-8")

    def _all(self) -> dict[str, dict]:
        self.initialize()
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self, records: dict[str, dict]) -> None:
        self.path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, file_id: UUID, session_id: UUID) -> FileRecord:
        item = self._all().get(str(file_id))
        if not item:
            raise FileReadError("File is not registered")
        record = FileRecord.model_validate(item)
        if record.session_id != session_id:
            raise FileReadError("Session isolation")
        return record

    def list_for_session(self, session_id: UUID) -> list[FileRecord]:
        return [FileRecord.model_validate(value) for value in self._all().values() if value["session_id"] == str(session_id)]

    @staticmethod
    def _kind(extension: str) -> str:
        if extension in IMAGE_EXTENSIONS:
            return "image"
        if extension == ".json":
            return "json"
        return "table"

    def _validate_content(self, target: Path, extension: str) -> None:
        head = target.read_bytes()[:32]
        if extension == ".png" and not head.startswith(b"\x89PNG\r\n\x1a\n"):
            raise InvalidMimeError()
        if extension in {".jpg", ".jpeg"} and not head.startswith(b"\xff\xd8\xff"):
            raise InvalidMimeError()
        if extension == ".webp" and not (head.startswith(b"RIFF") and head[8:12] == b"WEBP"):
            raise InvalidMimeError()
        if extension == ".xlsx":
            if not zipfile.is_zipfile(target):
                raise InvalidMimeError()
            with zipfile.ZipFile(target) as archive:
                total = sum(info.file_size for info in archive.infolist())
                if total > self.settings.max_file_size * 20:
                    raise FileTooLargeError()
        if extension == ".xls" and not head.startswith(b"\xd0\xcf\x11\xe0"):
            raise InvalidMimeError()
        if extension == ".json":
            try:
                json.loads(target.read_text(encoding="utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise FileReadError() from exc
        if extension in IMAGE_EXTENSIONS:
            try:
                with Image.open(target) as image:
                    image.verify()
                with Image.open(target) as image:
                    if image.width * image.height > self.settings.max_image_pixels:
                        raise FileTooLargeError()
            except (UnidentifiedImageError, OSError) as exc:
                raise InvalidMimeError() from exc

    async def save_upload(self, upload: UploadFile, session_id: UUID) -> FileRecord:
        self.initialize()
        original_name = safe_filename(upload.filename or "")
        extension = Path(original_name).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise UnsupportedFileError()
        file_id = uuid4()
        saved_name = f"{file_id}{extension}"
        session_dir = inside(self.settings.uploads_dir, self.settings.uploads_dir / str(session_id))
        session_dir.mkdir(parents=True, exist_ok=True)
        target = inside(session_dir, session_dir / saved_name)
        size = 0
        try:
            with target.open("wb") as destination:
                while chunk := await upload.read(64 * 1024):
                    size += len(chunk)
                    if size > self.settings.max_file_size:
                        destination.close()
                        target.unlink(missing_ok=True)
                        raise FileTooLargeError()
                    destination.write(chunk)
        except FileTooLargeError:
            raise
        except OSError as exc:
            target.unlink(missing_ok=True)
            raise FileReadError() from exc
        finally:
            await upload.close()
        if size == 0:
            target.unlink(missing_ok=True)
            raise EmptyFileError()
        try:
            self._validate_content(target, extension)
        except Exception:
            target.unlink(missing_ok=True)
            raise
        record = FileRecord(
            file_id=file_id, original_name=original_name, saved_name=saved_name, extension=extension,
            content_type=upload.content_type or "application/octet-stream", size_bytes=size,
            kind=self._kind(extension), session_id=session_id,
            relative_path=str(target.relative_to(self.settings.storage_root)).replace("\\", "/"),
            storage_url=f"/files/{file_id}",
        )
        records = self._all()
        records[str(record.file_id)] = record.model_dump(mode="json")
        self._save(records)
        return record

    def path_for(self, record: FileRecord) -> Path:
        return inside(self.settings.storage_root, self.settings.storage_root / record.relative_path)
